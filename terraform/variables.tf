variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "ap-south-1"
}

variable "cluster_name" {
  description = "Name of the EKS cluster"
  type        = string
  default     = "studydesk-eks"
}

variable "environment" {
  description = "Environment tag (dev / prod)"
  type        = string
  default     = "dev"
}

variable "node_instance_types" {
  description = "Instance types for the managed node group"
  type        = list(string)
  default     = ["t3.medium"]
}

variable "node_desired_size" {
  description = "Number of worker nodes"
  type        = number
  default     = 2
}
