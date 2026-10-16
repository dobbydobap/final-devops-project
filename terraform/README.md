# Terraform: VPC + EKS for StudyDesk

Creates the AWS side of the deployment in `ap-south-1`:

- a VPC (`10.20.0.0/16`) with 2 public and 2 private subnets across two availability zones
- one NAT gateway (shared, to keep cost down) so private nodes can pull images
- an EKS 1.31 cluster with a managed node group (2 × t3.medium by default)

Both are built from the community `terraform-aws-modules` VPC and EKS modules, pinned to exact
versions.

```bash
cp terraform.tfvars.example terraform.tfvars   # edit if needed
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
aws eks update-kubeconfig --region ap-south-1 --name studydesk-eks
terraform destroy
```

Credentials come from `aws configure` or `AWS_*` environment variables. Nothing secret is in this
folder, and `terraform.tfvars`, `.terraform/` and state files are git-ignored.

> Cost: EKS (control plane + nodes) and the NAT gateway are billed by the hour and are not covered by
> the free tier. Run `terraform destroy` as soon as you are done.
