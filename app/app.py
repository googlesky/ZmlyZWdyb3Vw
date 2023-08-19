import boto3
import datetime
import json
from flask import Flask, request

app = Flask(__name__)

@app.route('/update_lc', methods=['POST'])
def update_lc():
    asg_name = request.json['asg_name']

    # Create a timestamp prefix for the new LC name
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_lc_name = f"{timestamp}-{asg_name}-LC"

    # Create an EC2 client
    ec2_client = boto3.client('ec2')

    # Retrieve the instances belonging to the ASG
    asg_client = boto3.client('autoscaling')
    response = asg_client.describe_auto_scaling_groups(AutoScalingGroupNames=[asg_name])
    auto_scaling_groups = response['AutoScalingGroups']
    if not auto_scaling_groups:
        return json.dumps({'result': False, 'error': f"No Auto Scaling Group found with name {asg_name}"})
    instances = auto_scaling_groups[0]['Instances']

    # Select any instance from the ASG
    instance_id = instances[0]['InstanceId']

    # Create an AMI from the selected instance
    response = ec2_client.create_image(
        InstanceId=instance_id,
        Name=f"{timestamp}-{asg_name}-AMI",
        Description="AMI created from an instance in the ASG"
    )
    image_id = response['ImageId']

    # Retrieve the current LC of the ASG
    response = asg_client.describe_launch_configurations(LaunchConfigurationNames=[asg_name])
    launch_configurations = response['LaunchConfigurations']
    if not launch_configurations:
        return json.dumps({'result': False, 'error': f"No launch configuration found with name {asg_name}"})
    current_lc = launch_configurations[0]

    # Create a new LC based on the current LC with the updated AMI
    new_lc = current_lc.copy()
    new_lc['LaunchConfigurationName'] = new_lc_name
    new_lc['ImageId'] = image_id

    # Create the new LC
    response = asg_client.create_launch_configuration(**new_lc)

    # Update the ASG to use the new LC
    response = asg_client.update_auto_scaling_group(
        AutoScalingGroupName=asg_name,
        LaunchConfigurationName=new_lc_name
    )

    # Return the JSON response
    response = {
        'result': True,
        'LC': new_lc_name
    }
    return json.dumps(response)

if __name__ == '__main__':
    app.run()