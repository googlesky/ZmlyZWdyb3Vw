# Define the provider (e.g., AWS)
provider "aws" {
  region = "ap-southeast-1"
}

# Create a VPC
resource "aws_vpc" "example" {
  cidr_block = "10.0.0.0/16"
}

# Create a subnet within the VPC
resource "aws_subnet" "example" {
  vpc_id                  = aws_vpc.example.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "ap-southeast-1a"
}

# Create a launch template
resource "aws_launch_template" "example" {
  name          = "example-launch-template"
  image_id      = "ami-091a58610910a87a9"
  instance_type = "t2.micro"

  # Additional configuration options (e.g., security groups, user data) can be added here
}

# Create an Auto Scaling Group
resource "aws_autoscaling_group" "example" {
  name                 = "example-asg"
  launch_template {
    id = aws_launch_template.example.id
  }
  min_size             = 1
  max_size             = 5
  desired_capacity     = 1
  vpc_zone_identifier  = [aws_subnet.example.id]

  # Additional configuration options (e.g., load balancers, tags) can be added here
}

# Define scaling policies (optional)
resource "aws_autoscaling_policy" "example_scale_out" {
  name                   = "example-scale-out-policy"
  policy_type            = "SimpleScaling"
  autoscaling_group_name = aws_autoscaling_group.example.name

  adjustment_type         = "ChangeInCapacity"
  scaling_adjustment      = 1
  cooldown                = 300
}

resource "aws_autoscaling_policy" "example_scale_in" {
  name                   = "example-scale-in-policy"
  policy_type            = "SimpleScaling"
  autoscaling_group_name = aws_autoscaling_group.example.name

  adjustment_type         = "ChangeInCapacity"
  scaling_adjustment      = -1
  cooldown                = 300
}