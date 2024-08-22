import logging
import time
import threading

from django.db import connection as db_connection
from .ssh_client import run_command

logger = logging.getLogger('wireguard')


class WireGuardProvisioner:

    def __init__(self, server):
        self.server = server

    def _append_log(self, message):
        from apps.server.models import ServerConfig
        ts    = time.strftime('%H:%M:%S')
        entry = f'[{ts}] {message}\n'
        obj   = ServerConfig.objects.get(pk=self.server.pk)
        obj.provisioning_log += entry
        obj.save(update_fields=['provisioning_log'])

    def _set_status(self, status):
        from apps.server.models import ServerConfig
        ServerConfig.objects.filter(pk=self.server.pk).update(
            provisioning_status=status
        )

    def _install_and_configure(self):
        from apps.server.models import ServerConfig
        from wireguard.commands import write_config
        from wireguard.key_manager import encrypt
        from wireguard.ip_allocator import IPAllocator

        self._append_log('Step 1/6: Testing SSH connection...')
        run_command('echo "SSH OK"', self.server)
        self._append_log('SSH connection successful.')

        self._append_log('Step 2/6: Installing WireGuard...')
        run_command(
            'export DEBIAN_FRONTEND=noninteractive && sudo apt-get update -y',
            self.server
        )
        run_command(
            'export DEBIAN_FRONTEND=noninteractive && sudo apt-get install -y wireguard iptables',
            self.server
        )
        run_command(
            "echo 'net.ipv4.ip_forward=1' | sudo tee -a /etc/sysctl.conf && sudo sysctl -p",
            self.server
        )
        self._append_log('WireGuard installed.')

        self._append_log('Step 3/6: Generating WireGuard keys...')
        private_key, _ = run_command('wg genkey', self.server)
        private_key    = private_key.strip()
        public_key, _  = run_command(f'echo "{private_key}" | wg pubkey', self.server)
        public_key     = public_key.strip()
        self._append_log('Keys generated.')

        self._append_log('Step 4/6: Detecting network interface...')
        iface, _ = run_command(
            "ip route | grep default | awk '{print $5}' | head -1",
            self.server
        )
        iface = iface.strip() or 'eth0'
        self._append_log(f'Network interface: {iface}')

        self._append_log('Step 5/6: Writing WireGuard config...')
        post_up = (
            f'iptables -A FORWARD -i {self.server.interface_name} -j ACCEPT; '
            f'iptables -A FORWARD -o {self.server.interface_name} -j ACCEPT; '
            f'iptables -t nat -A POSTROUTING -o {iface} -j MASQUERADE'
        )
        post_down = (
            f'iptables -D FORWARD -i {self.server.interface_name} -j ACCEPT; '
            f'iptables -D FORWARD -o {self.server.interface_name} -j ACCEPT; '
            f'iptables -t nat -D POSTROUTING -o {iface} -j MASQUERADE'
        )
        config_content = (
            f'[Interface]\n'
            f'Address = {self.server.address}\n'
            f'SaveConfig = true\n'
            f'PostUp = {post_up}\n'
            f'PostDown = {post_down}\n'
            f'ListenPort = {self.server.listen_port}\n'
            f'PrivateKey = {private_key}\n'
        )
        write_config(self.server, self.server.interface_name, config_content)
        run_command(
            f'sudo chmod 600 /etc/wireguard/{self.server.interface_name}.conf',
            self.server
        )
        self._append_log('Config written to /etc/wireguard/.')

        self._append_log('Step 6/6: Starting WireGuard service...')
        run_command(
            f'sudo systemctl enable wg-quick@{self.server.interface_name}',
            self.server
        )
        run_command(
            f'sudo systemctl start wg-quick@{self.server.interface_name}',
            self.server
        )
        self._append_log('WireGuard service started.')

        ServerConfig.objects.filter(pk=self.server.pk).update(
            public_key=public_key,
            private_key=encrypt(private_key),
            post_up=post_up,
            post_down=post_down,
        )
        self._append_log('Keys saved to database.')

        server = ServerConfig.objects.get(pk=self.server.pk)
        IPAllocator(server).populate_pool()
        self._append_log('IP pool populated.')

    # Existing VM path

    def provision_existing_vm(self):
        self._set_status('provisioning')
        try:
            self._install_and_configure()
            self._set_status('provisioned')
            self._append_log('Provisioning complete. Server is ready.')
        except Exception as e:
            self._append_log(f'ERROR: {e}')
            self._set_status('failed')
            logger.exception('Provisioning failed for server %s', self.server.pk)

    def start_provision_existing_vm(self):
        def run():
            try:
                self.provision_existing_vm()
            finally:
                db_connection.close()
        threading.Thread(target=run, daemon=True).start()

    # GCP VM path

    @staticmethod
    def generate_ssh_keypair():
        import paramiko
        import io
        key     = paramiko.RSAKey.generate(2048)
        buf     = io.StringIO()
        key.write_private_key(buf)
        private = buf.getvalue()
        public  = f'ssh-rsa {key.get_base64()}'
        return private, public

    def create_gcp_vm(self, project_id, zone, machine_type, sa_json_str, ssh_user):
        import json
        from google.cloud import compute_v1
        from google.oauth2 import service_account

        self._append_log('Generating SSH key pair...')
        private_key_str, public_key_str = self.generate_ssh_keypair()

        sa_info     = json.loads(sa_json_str)
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        client        = compute_v1.InstancesClient(credentials=credentials)
        instance_name = f'wireguard-{self.server.pk}-{int(time.time())}'

        disk                   = compute_v1.AttachedDisk()
        disk.auto_delete       = True
        disk.boot              = True
        init                   = compute_v1.AttachedDiskInitializeParams()
        init.source_image      = 'projects/debian-cloud/global/images/family/debian-12'
        init.disk_size_gb      = 20
        disk.initialize_params = init

        nic                = compute_v1.NetworkInterface()
        access             = compute_v1.AccessConfig()
        access.name        = 'External NAT'
        access.type_       = 'ONE_TO_ONE_NAT'
        nic.access_configs = [access]

        instance                    = compute_v1.Instance()
        instance.name               = instance_name
        instance.machine_type       = f'zones/{zone}/machineTypes/{machine_type}'
        instance.disks              = [disk]
        instance.network_interfaces = [nic]
        instance.metadata           = compute_v1.Metadata(items=[
            compute_v1.Items(
                key='ssh-keys',
                value=f'{ssh_user}:{public_key_str} {ssh_user}'
            )
        ])

        self._append_log(f'Creating VM: {instance_name} in {zone}...')
        op = client.insert(project=project_id, zone=zone, instance_resource=instance)
        self._append_log('Waiting for VM creation (this may take 1-2 minutes)...')
        op.result(timeout=300)
        self._append_log('VM created.')

        info        = client.get(project=project_id, zone=zone, instance=instance_name)
        external_ip = info.network_interfaces[0].access_configs[0].nat_i_p
        self._append_log(f'VM external IP: {external_ip}')

        return external_ip, private_key_str, instance_name

    def provision_gcp_vm(self, project_id, zone, machine_type, sa_json_str):
        from apps.server.models import ServerConfig
        from wireguard.key_manager import encrypt

        self._set_status('provisioning')
        try:
            ssh_user = self.server.ssh_user
            external_ip, ssh_private_key, instance_name = self.create_gcp_vm(
                project_id, zone, machine_type, sa_json_str, ssh_user
            )

            ServerConfig.objects.filter(pk=self.server.pk).update(
                public_ip=external_ip,
                ssh_host=external_ip,
                ssh_key_encrypted=encrypt(ssh_private_key),
                gcp_instance_name=instance_name,
                gcp_zone=zone,
                gcp_project_id=project_id,
            )
            self.server = ServerConfig.objects.get(pk=self.server.pk)

            self._append_log('Waiting for SSH to become available...')
            time.sleep(30)
            for attempt in range(10):
                try:
                    run_command('echo "SSH OK"', self.server)
                    self._append_log('SSH is available.')
                    break
                except Exception:
                    self._append_log(f'SSH not ready, retrying ({attempt + 1}/10)...')
                    time.sleep(10)
            else:
                raise Exception('SSH did not become available after VM creation.')

            self._install_and_configure()
            self._set_status('provisioned')
            self._append_log('Provisioning complete. Server is ready.')

        except Exception as e:
            self._append_log(f'ERROR: {e}')
            self._set_status('failed')
            logger.exception('GCP provisioning failed for server %s', self.server.pk)

    def destroy_gcp_vm(self, project_id, zone, instance_name, sa_json_str):
        import json
        from google.cloud import compute_v1
        from google.oauth2 import service_account

        sa_info     = json.loads(sa_json_str)
        credentials = service_account.Credentials.from_service_account_info(
            sa_info,
            scopes=['https://www.googleapis.com/auth/cloud-platform']
        )
        client = compute_v1.InstancesClient(credentials=credentials)
        op     = client.delete(project=project_id, zone=zone, instance=instance_name)
        op.result(timeout=300)
        logger.info('GCP VM %s deleted.', instance_name)

    def start_provision_gcp_vm(self, project_id, zone, machine_type, sa_json_str):
        def run():
            try:
                self.provision_gcp_vm(project_id, zone, machine_type, sa_json_str)
            finally:
                db_connection.close()
        threading.Thread(target=run, daemon=True).start()

    # AWS VM path

    def create_aws_vm(self, region, instance_type, aws_access_key, aws_secret_key, ssh_user):
        import boto3

        self._append_log('Generating SSH key pair...')
        private_key_str, public_key_str = self.generate_ssh_keypair()

        self._append_log(f'Connecting to AWS region {region}...')
        ec2 = boto3.client(
            'ec2',
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
        )

        sg_name = f'wireguard-{self.server.pk}-{int(time.time())}'
        self._append_log(f'Creating security group {sg_name}...')
        sg    = ec2.create_security_group(
            GroupName=sg_name,
            Description='WireGuard Manager auto-created security group',
        )
        sg_id = sg['GroupId']
        ec2.authorize_security_group_ingress(
            GroupId=sg_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 22,
                    'ToPort': 22,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                },
                {
                    'IpProtocol': 'udp',
                    'FromPort': self.server.listen_port,
                    'ToPort': self.server.listen_port,
                    'IpRanges': [{'CidrIp': '0.0.0.0/0'}],
                },
            ]
        )
        self._append_log('Security group created.')

        key_name = f'wireguard-key-{self.server.pk}-{int(time.time())}'
        ec2.import_key_pair(
            KeyName=key_name,
            PublicKeyMaterial=public_key_str.encode('utf-8'),
        )
        self._append_log('SSH key imported.')

        self._append_log('Finding latest Ubuntu 22.04 AMI...')
        images = ec2.describe_images(
            Filters=[
                {'Name': 'name', 'Values': ['ubuntu/images/hvm-ssd/ubuntu-jammy-22.04-amd64-*']},
                {'Name': 'state', 'Values': ['available']},
            ],
            Owners=['099720109477'],
        )
        ami_id = sorted(
            images['Images'],
            key=lambda x: x['CreationDate'],
            reverse=True
        )[0]['ImageId']
        self._append_log(f'Using AMI: {ami_id}')

        self._append_log(f'Launching EC2 instance ({instance_type})...')
        response    = ec2.run_instances(
            ImageId=ami_id,
            InstanceType=instance_type,
            MinCount=1,
            MaxCount=1,
            KeyName=key_name,
            SecurityGroupIds=[sg_id],
            BlockDeviceMappings=[{
                'DeviceName': '/dev/sda1',
                'Ebs': {'VolumeSize': 20, 'DeleteOnTermination': True},
            }],
        )
        instance_id = response['Instances'][0]['InstanceId']
        self._append_log(f'Instance launched: {instance_id}. Waiting for it to start...')

        waiter = ec2.get_waiter('instance_running')
        waiter.wait(InstanceIds=[instance_id])
        self._append_log('Instance is running.')

        info        = ec2.describe_instances(InstanceIds=[instance_id])
        external_ip = info['Reservations'][0]['Instances'][0]['PublicIpAddress']
        self._append_log(f'Instance public IP: {external_ip}')

        return external_ip, private_key_str, instance_id

    def provision_aws_vm(self, region, instance_type, aws_access_key, aws_secret_key):
        from apps.server.models import ServerConfig
        from wireguard.key_manager import encrypt

        self._set_status('provisioning')
        try:
            ssh_user = self.server.ssh_user
            external_ip, ssh_private_key, instance_id = self.create_aws_vm(
                region, instance_type, aws_access_key, aws_secret_key, ssh_user
            )

            ServerConfig.objects.filter(pk=self.server.pk).update(
                public_ip=external_ip,
                ssh_host=external_ip,
                ssh_key_encrypted=encrypt(ssh_private_key),
                aws_instance_id=instance_id,
                aws_region=region,
            )
            self.server = ServerConfig.objects.get(pk=self.server.pk)

            self._append_log('Waiting for SSH to become available...')
            time.sleep(30)
            for attempt in range(12):
                try:
                    run_command('echo "SSH OK"', self.server)
                    self._append_log('SSH is available.')
                    break
                except Exception:
                    self._append_log(f'SSH not ready, retrying ({attempt + 1}/12)...')
                    time.sleep(10)
            else:
                raise Exception('SSH did not become available after instance launch.')

            self._install_and_configure()
            self._set_status('provisioned')
            self._append_log('Provisioning complete. Server is ready.')

        except Exception as e:
            self._append_log(f'ERROR: {e}')
            self._set_status('failed')
            logger.exception('AWS provisioning failed for server %s', self.server.pk)

    def destroy_aws_vm(self, instance_id, region, aws_access_key, aws_secret_key):
        import boto3

        ec2 = boto3.client(
            'ec2',
            region_name=region,
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
        )
        ec2.terminate_instances(InstanceIds=[instance_id])
        waiter = ec2.get_waiter('instance_terminated')
        waiter.wait(InstanceIds=[instance_id])
        logger.info('AWS instance %s terminated.', instance_id)

    def start_provision_aws_vm(self, region, instance_type, aws_access_key, aws_secret_key):
        def run():
            try:
                self.provision_aws_vm(region, instance_type, aws_access_key, aws_secret_key)
            finally:
                db_connection.close()
        threading.Thread(target=run, daemon=True).start()