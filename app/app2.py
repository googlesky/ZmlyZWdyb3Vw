from flask import Flask, request, jsonify
import boto3
import botocore
import datetime
import json
import time

app = Flask(__name__)

def create_ami_from_instance(instance_id):
    ec2_client = boto3.client('ec2')
    
    # Generate a unique name for the AMI using timestamp
    ami_name = 'AMI_' + datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    
    # Create the AMI with retry mechanism
    while True:
        try:
            response = ec2_client.create_image(
                InstanceId=instance_id,
                Name=ami_name
            )
            return response['ImageId']
        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'InvalidRequest':
                # Another CreateImage operation is in progress; wait and retry
                time.sleep(10)
            else:
                raise

def update_launch_template(launch_template_id, ami_id):
    ec2_client = boto3.client('ec2')
    
    # Get the current launch template details
    response = ec2_client.describe_launch_template_versions(
        LaunchTemplateId=launch_template_id,
        Versions=['$Latest']
    )
    
    # Preserve existing configurations
    launch_template_data = response['LaunchTemplateVersions'][0]['LaunchTemplateData']
    
    # Check if LaunchTemplateName key exists
    if 'LaunchTemplateName' in launch_template_data:
        # Set the new AMI ID
        launch_template_data['ImageId'] = ami_id
    
        # Set the new launch template name with a timestamp prefix
        new_template_name = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_' + launch_template_data['LaunchTemplateName']
        launch_template_data['LaunchTemplateName'] = new_template_name
        
        # Create a new launch template version with the updated configurations
        response = ec2_client.create_launch_template_version(
            LaunchTemplateId=launch_template_id,
            LaunchTemplateData=launch_template_data,
            SourceVersion='$Latest'
        )
        
        return new_template_name
    else:
        # Create a new launch template when LaunchTemplateName key is not found
        new_template_name = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S') + '_DefaultLaunchTemplate'
        
        response = ec2_client.create_launch_template(
            LaunchTemplateName=new_template_name,
            LaunchTemplateData=launch_template_data
        )
        
        return new_template_name

def update_asg_launch_template(asg_name, new_launch_template_name):
    autoscaling_client = boto3.client('autoscaling')
    
    # Get the current ASG details
    response = autoscaling_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name]
    )
    
    # Update the ASG to use the new launch template
    response = autoscaling_client.update_auto_scaling_group(
        AutoScalingGroupName=asg_name,
        LaunchTemplate={
            'LaunchTemplateName': new_launch_template_name,
            'Version': '$Latest'
        }
    )

def update_asg_with_new_ami(asg_name):
    # Retrieve the instances in the ASG
    autoscaling_client = boto3.client('autoscaling')
    response = autoscaling_client.describe_auto_scaling_groups(
        AutoScalingGroupNames=[asg_name]
    )
    instances = response['AutoScalingGroups'][0]['Instances']
    
    # Select an instance to create the AMI from
    instance_id = instances[0]['InstanceId']
    
    # Create the AMI
    ami_id = create_ami_from_instance(instance_id)
    
    # Retrieve the launch template ID
    launch_template_id = instances[0]['LaunchTemplate']['LaunchTemplateId']
    
    # Update the launch template
    new_launch_template_name = update_launch_template(launch_template_id, ami_id)
    
    # Update the ASG with the new launch template
    update_asg_launch_template(asg_name, new_launch_template_name)
    
    # Return the JSON response
    response = {
        'result': True,
        'launch_templates': new_launch_template_name
    }
    
    return json.dumps(response)

@app.route('/update_asg_with_new_ami', methods=['POST'])
def update_asg_with_new_ami_api():
    # Parse the request parameters
    asg_name = request.form['asg_name']
    
    # Call the update_asg_with_new_ami function
    response = update_asg_with_new_ami(asg_name)
    
    # Return the response as a JSON object
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)
