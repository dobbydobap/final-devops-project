data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  azs = slice(data.aws_availability_zones.available.names, 0, 2)
}

module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.8.1"

  name = "studydesk-vpc"
  cidr = "10.20.0.0/16"
  azs  = local.azs

  public_subnets          = ["10.20.101.0/24", "10.20.102.0/24"]
  map_public_ip_on_launch = true
  private_subnets         = ["10.20.1.0/24", "10.20.2.0/24"]

  # one NAT gateway instead of one per AZ keeps the bill down for a student project
  enable_nat_gateway   = true
  single_nat_gateway   = true
  enable_dns_hostnames = true

  # tags the AWS load balancer controller looks for when it creates ELBs
  public_subnet_tags = {
    "kubernetes.io/role/elb" = 1
  }
  private_subnet_tags = {
    "kubernetes.io/role/internal-elb" = 1
  }
}

module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "20.37.1"

  cluster_name    = var.cluster_name
  cluster_version = "1.31"

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  cluster_endpoint_public_access           = true
  enable_cluster_creator_admin_permissions = true

  eks_managed_node_groups = {
    main = {
      instance_types = var.node_instance_types
      min_size       = 1
      max_size       = 4
      desired_size   = var.node_desired_size
    }
  }
}
