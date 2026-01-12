from aws_cdk import (
    Stack,
    Duration,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr as ecr,
    aws_ecs_patterns as ecs_patterns,
    aws_rds as rds,
    aws_iam as iam,
    aws_logs as logs,
    aws_elasticloadbalancingv2 as elbv2,
    aws_servicediscovery as servicediscovery,
)
from constructs import Construct


class AsteriskPbxStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # ========== VPC and Networking ==========
        vpc = ec2.Vpc(
            self, "PBXVpc",
            max_azs=2,
            nat_gateways=1,
            subnet_configuration=[
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PUBLIC,
                    name="Public",
                    cidr_mask=24,
                ),
                ec2.SubnetConfiguration(
                    subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS,
                    name="Private",
                    cidr_mask=24,
                ),
            ],
        )

        # ========== Security Groups ==========
        # MySQL Security Group
        mysql_sg = ec2.SecurityGroup(
            self, "MySQLSecurityGroup",
            vpc=vpc,
            description="Security group for MySQL database",
            allow_all_outbound=True,
        )
        mysql_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(3306),
            description="Allow MySQL from VPC",
        )

        # FreeSWITCH Security Group
        freeswitch_sg = ec2.SecurityGroup(
            self, "FreeSWITCHSecurityGroup",
            vpc=vpc,
            description="Security group for FreeSWITCH",
            allow_all_outbound=True,
        )
        freeswitch_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.udp(5060),
            description="SIP UDP",
        )
        freeswitch_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(5060),
            description="SIP TCP",
        )
        freeswitch_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(8021),
            description="ESL port",
        )
        freeswitch_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.range(10000, 20000),
            description="RTP media ports",
        )

        # Kamailio Security Group
        kamailio_sg = ec2.SecurityGroup(
            self, "KamailioSecurityGroup",
            vpc=vpc,
            description="Security group for Kamailio",
            allow_all_outbound=True,
        )
        kamailio_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.udp(5060),
            description="SIP UDP",
        )
        kamailio_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(5060),
            description="SIP TCP",
        )
        kamailio_sg.add_ingress_rule(
            peer=freeswitch_sg,
            connection=ec2.Port.all_tcp(),
            description="Allow from FreeSWITCH",
        )
        kamailio_sg.add_ingress_rule(
            peer=freeswitch_sg,
            connection=ec2.Port.all_udp(),
            description="Allow UDP from FreeSWITCH",
        )

        # Python App Security Group
        python_app_sg = ec2.SecurityGroup(
            self, "PythonAppSecurityGroup",
            vpc=vpc,
            description="Security group for Python Flask app",
            allow_all_outbound=True,
        )
        python_app_sg.add_ingress_rule(
            peer=ec2.Peer.any_ipv4(),
            connection=ec2.Port.tcp(5001),
            description="Flask app port",
        )
        python_app_sg.add_ingress_rule(
            peer=ec2.Peer.ipv4(vpc.vpc_cidr_block),
            connection=ec2.Port.tcp(5001),
            description="Flask app from VPC",
        )

        # ========== RDS MySQL Database ==========
        mysql_db = rds.DatabaseInstance(
            self, "MySQLDatabase",
            engine=rds.DatabaseInstanceEngine.mysql(
                version=rds.MysqlEngineVersion.VER_8_0
            ),
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.T3,
                ec2.InstanceSize.MICRO
            ),
            vpc=vpc,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PRIVATE_WITH_EGRESS
            ),
            security_groups=[mysql_sg],
            credentials=rds.Credentials.from_generated_secret(
                "mysqladmin",
                exclude_characters="\"@/"
            ),
            database_name="voipdb",
            removal_policy=RemovalPolicy.DESTROY,  # Change for production
            deletion_protection=False,
            multi_az=False,  # Enable for production
        )

        # ========== ECS Cluster ==========
        cluster = ecs.Cluster(
            self, "PBXCluster",
            vpc=vpc,
            container_insights=True,
        )

        # ========== CloudMap Service Discovery ==========
        namespace = servicediscovery.PrivateDnsNamespace(
            self, "PBXNamespace",
            name="pbx.local",
            vpc=vpc,
        )

        # ========== ECR Repositories ==========
        freeswitch_repo = ecr.Repository(
            self, "FreeSWITCHRepository",
            repository_name="freeswitch-pbx",
            removal_policy=RemovalPolicy.DESTROY,
        )

        kamailio_repo = ecr.Repository(
            self, "KamailioRepository",
            repository_name="kamailio-pbx",
            removal_policy=RemovalPolicy.DESTROY,
        )

        python_app_repo = ecr.Repository(
            self, "PythonAppRepository",
            repository_name="python-brain-pbx",
            removal_policy=RemovalPolicy.DESTROY,
        )

        # ========== Task Definitions ==========
        
        # FreeSWITCH Task Definition
        freeswitch_task = ecs.FargateTaskDefinition(
            self, "FreeSWITCHTask",
            memory_limit_mib=2048,
            cpu=1024,
        )
        
        freeswitch_container = freeswitch_task.add_container(
            "freeswitch",
            image=ecs.ContainerImage.from_registry(
                "freeswitch/freeswitch:latest"
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="freeswitch",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
            environment={
                "ESL_PASSWORD": "ClueCon",
            },
        )
        freeswitch_container.add_port_mappings(
            ecs.PortMapping(container_port=5060, protocol=ecs.Protocol.UDP),
            ecs.PortMapping(container_port=5060, protocol=ecs.Protocol.TCP),
            ecs.PortMapping(container_port=8021, protocol=ecs.Protocol.TCP),
            ecs.PortMapping(container_port=10000, protocol=ecs.Protocol.UDP),
        )

        # Kamailio Task Definition
        kamailio_task = ecs.FargateTaskDefinition(
            self, "KamailioTask",
            memory_limit_mib=512,
            cpu=256,
        )
        
        kamailio_container = kamailio_task.add_container(
            "kamailio",
            image=ecs.ContainerImage.from_registry(
                "ghcr.io/kamailio/kamailio:5.8.2-jammy"
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="kamailio",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
        )
        kamailio_container.add_port_mappings(
            ecs.PortMapping(container_port=5060, protocol=ecs.Protocol.UDP),
            ecs.PortMapping(container_port=5060, protocol=ecs.Protocol.TCP),
        )

        # Python App Task Definition
        python_app_task = ecs.FargateTaskDefinition(
            self, "PythonAppTask",
            memory_limit_mib=512,
            cpu=256,
        )
        
        # Get MySQL endpoint from RDS
        mysql_endpoint = mysql_db.instance_endpoint.hostname
        
        python_app_container = python_app_task.add_container(
            "python-app",
            image=ecs.ContainerImage.from_ecr_repository(
                python_app_repo, "latest"
            ),
            logging=ecs.LogDrivers.aws_logs(
                stream_prefix="python-app",
                log_retention=logs.RetentionDays.ONE_WEEK,
            ),
            environment={
                "MYSQL_HOST": mysql_endpoint,
                "MYSQL_USER": "mysqladmin",
                "MYSQL_DATABASE": "voipdb",
                "FS_HOST": "freeswitch.pbx.local",
                "FS_PORT": "8021",
                "FS_PASSWORD": "ClueCon",
            },
            secrets={
                "MYSQL_PASSWORD": ecs.Secret.from_secrets_manager(
                    mysql_db.secret, "password"
                ),
            },
        )
        python_app_container.add_port_mappings(
            ecs.PortMapping(container_port=5001, protocol=ecs.Protocol.TCP),
        )

        # ========== ECS Services ==========
        
        # FreeSWITCH Service
        freeswitch_service = ecs.FargateService(
            self, "FreeSWITCHService",
            cluster=cluster,
            task_definition=freeswitch_task,
            desired_count=1,
            security_groups=[freeswitch_sg],
            cloud_map_options=ecs.CloudMapOptions(
                name="freeswitch",
                cloud_map_namespace=namespace,
            ),
        )

        # Kamailio Service
        kamailio_service = ecs.FargateService(
            self, "KamailioService",
            cluster=cluster,
            task_definition=kamailio_task,
            desired_count=1,
            security_groups=[kamailio_sg],
            cloud_map_options=ecs.CloudMapOptions(
                name="kamailio",
                cloud_map_namespace=namespace,
            ),
        )

        # Python App Service with Load Balancer
        python_app_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "PythonAppService",
            cluster=cluster,
            task_definition=python_app_task,
            desired_count=1,
            public_load_balancer=True,
            listener_port=5001,
            security_groups=[python_app_sg],
            cloud_map_options=ecs.CloudMapOptions(
                name="python-app",
                cloud_map_namespace=namespace,
            ),
        )

        # ========== Network Load Balancer for SIP ==========
        sip_nlb = elbv2.NetworkLoadBalancer(
            self, "SIPLoadBalancer",
            vpc=vpc,
            internet_facing=True,
            cross_zone_enabled=True,
        )

        # Target groups for Kamailio (primary SIP proxy)
        kamailio_tcp_target = elbv2.NetworkTargetGroup(
            self, "KamailioTCPTarget",
            vpc=vpc,
            port=5060,
            protocol=elbv2.Protocol.TCP,
            health_check=elbv2.HealthCheck(
                protocol=elbv2.Protocol.TCP,
                enabled=True,
            ),
        )

        kamailio_udp_target = elbv2.NetworkTargetGroup(
            self, "KamailioUDPTarget",
            vpc=vpc,
            port=5060,
            protocol=elbv2.Protocol.UDP,
            health_check=elbv2.HealthCheck(
                protocol=elbv2.Protocol.TCP,
                port="5060",
                enabled=True,
            ),
        )

        # Configure Kamailio service with Network Load Balancer
        kamailio_service.attach_to_network_target_group(kamailio_tcp_target)
        kamailio_service.attach_to_network_target_group(kamailio_udp_target)

        # TCP listener for SIP
        sip_tcp_listener = sip_nlb.add_listener(
            "SIPTCPListener",
            port=5060,
            protocol=elbv2.Protocol.TCP,
        )

        # UDP listener for SIP
        sip_udp_listener = sip_nlb.add_listener(
            "SIPUDPListener",
            port=5060,
            protocol=elbv2.Protocol.UDP,
        )

        sip_tcp_listener.add_target_groups("KamailioTCP", kamailio_tcp_target)
        sip_udp_listener.add_target_groups("KamailioUDP", kamailio_udp_target)

        # ========== IAM Permissions ==========
        # Allow Python app to read RDS secret
        mysql_db.secret.grant_read(python_app_task.task_role)

        # ========== Outputs ==========
        CfnOutput(
            self, "SIPEndpoint",
            value=f"sip://{sip_nlb.load_balancer_dns_name}:5060",
            description="SIP endpoint for clients",
        )

        CfnOutput(
            self, "PythonAppEndpoint",
            value=f"http://{python_app_service.load_balancer.load_balancer_dns_name}:5001",
            description="Python Flask app endpoint",
        )

        CfnOutput(
            self, "MySQLEndpoint",
            value=mysql_endpoint,
            description="MySQL database endpoint",
        )

        CfnOutput(
            self, "FreeSWITCHRepositoryURI",
            value=freeswitch_repo.repository_uri,
            description="ECR repository URI for FreeSWITCH",
        )

        CfnOutput(
            self, "KamailioRepositoryURI",
            value=kamailio_repo.repository_uri,
            description="ECR repository URI for Kamailio",
        )

        CfnOutput(
            self, "PythonAppRepositoryURI",
            value=python_app_repo.repository_uri,
            description="ECR repository URI for Python app",
        )

        CfnOutput(
            self, "MySQLSecretARN",
            value=mysql_db.secret.secret_arn,
            description="ARN of the MySQL secret in Secrets Manager",
        )

