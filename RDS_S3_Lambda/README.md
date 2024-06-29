# S3 To RDS DataLoader
## AWS Lambda function that processes files from an S3 bucket, loads data into an MySQL RDS database, and sends notifications via SNS and SQS.
### Prerequisites
1. **AWS Account:** Ensure you have an active AWS account.
2. **S3 Bucket:** Create an S3 bucket where files will be uploaded.
3. **MySQL RDS Instance:** Set up a MySQL RDS instance.
4. **SNS Topic:** Create an SNS topic for notifications.
5. **SQS Queue:** Create an SQS queue for message queuing.
### 1. Create an S3 Bucket
1. **Go to the S3 Console**
2. **Create a New Bucket:**
* Click on "Create bucket".
* Enter a unique bucket name.
* Choose the AWS region.
* Keep other settings as default or adjust according to your needs.
* Click on "Create bucket".
* uploaded a csv file into the bucket
  
  ![preview](images/task2.png)

### 2. Create a MySQL RDS Instance
1. **Go to the RDS Console**
2. **Create a Database:**
* Click on "Create database".
* Choose "Standard Create".
* Select "MySQL" as the engine type.
* Choose the version you prefer.
  
  ![preview](images/task5.png)
  ![preview](images/task6.png)

1. **Configure Database Settings:**
* Set "DB instance identifier", "Master username", and "Master password".
* Choose the instance class (e.g., db.t2.micro for free tier).
* Configure storage and connectivity options as needed.
  
  ![preview](images/task7.png)
  ![preview](images/task8.png)

1. **Create the Database:**
* Click on "Create database" and wait for the instance to be available.
  
  ![preview](images/task9.png)
  ![preview](images/task10.png)
  ![preview](images/task11.png)
  ![preview](images/task1.png)

### 3. Create an SQS Queue
1. **Go to the SQS Console**
2. **Create a New Queue:**
* Click on "Create queue".
* Choose the type (Standard or FIFO) and enter a name.
* Click on "Create queue".
  
  ![preview](images/task12.png)
  ![preview](images/task13.png)
  ![preview](images/task14.png)

### 4. Create an SNS Topic
1. **Go to the SNS Console**
2. **Create a New Topic:**
* Click on "Create topic".
* Choose the type (Standard or FIFO) and enter a name.
* Click on "Create topic".
  
  ![preview](images/task15.png)
  ![preview](images/task16.png)
  ![preview](images/task17.png)

### 5. Create two subcriptions 
1. **Go to the SNS Console**
2. **Create a New subcription:**
* Select the arn of above created topic.
* Select the protocol (email,sqs). 
   * For email give email id as endpoint
  
   ![preview](images/task18.png)

  * After creating the subscription you will get a email like below.
  
   ![preview](images/task20.png)
   
   * For amazon sqs give sqs arn as endpoint.
   
   ![preview](images/task19.png)
![preview](images/task21.png)

### 5. Set Up IAM Roles and Policies
1. **Create an IAM Role for Lambda:**
* Go to the IAM console.
* Create a new role with AWS Lambda as the trusted entity.
* Attach policies for S3, RDS,lambda execution role (for cloudwatch logs) SNS, and SQS access.
* Create role by selecting aws service as lambda and give the following policies.
  
      1. AmazonRDSFullAccess
      2. AmazonS3FullAccess
      3. AmazonSNSFullAccess
      4. AmazonSQSFullAccess
      5. AWSLambdaBasicExecutionRole
   
  ![preview](images/task3.png)
  ![preview](images/task4.png)
  
### 6. Create the Lambda Function
1. **Create the Lambda Function:**
* Go to the AWS Lambda console.
* Create a new function.
* Choose "Author from scratch".
* Configure function name, runtime (e.g., Python 3.8), and the IAM role created above.
* Configure Lambda Function to Trigger on S3 Events:
* In the Lambda function configuration, add an S3 trigger.
* Select the S3 bucket and configure the event type (e.g., s3:ObjectCreated:*).

![preview](images/task22.png)
### 7. Write the Lambda Function Code

```python
import boto3
import pymysql
import os
import logging

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = boto3.client('s3')
sns_client = boto3.client('sns')
sqs_client = boto3.client('sqs')

def lambda_handler(event, context):
    rds_endpoint = os.environ['RDS_ENDPOINT']
    db_user = os.environ['DB_USER']
    db_password = os.environ['DB_PASSWORD']
    db_name = os.environ['DB_NAME'].strip()  # Remove any leading/trailing spaces
    sns_topic_arn = os.environ['SNS_TOPIC_ARN']
    sqs_queue_url = os.environ['SQS_QUEUE_URL']
    bucket_name = os.environ['BUCKET_NAME']
    connection = None
    cursor = None

    try:
        connection = pymysql.connect(host=rds_endpoint, user=db_user, password=db_password)
        cursor = connection.cursor()
        # Ensure the database exists
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db_name}")
        cursor.execute(f"USE {db_name}")
        # Ensure the table exists before truncating it
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INT,
                title VARCHAR(100),
                tagline VARCHAR(100)
            )
        """)
        cursor.execute("TRUNCATE TABLE movies")
        for record in event['Records']:
            s3_object_key = record['s3']['object']['key']
            logger.info(f"Processing file: {s3_object_key}")
            # Download the file from S3
            download_path = f'/tmp/{s3_object_key}'
            s3_client.download_file(bucket_name, s3_object_key, download_path)
            logger.info(f"Downloaded file to {download_path}")
            # Load the data into Aurora MySQL
            with open(download_path, 'r') as file:
                csv_data = file.readlines()
                for row in csv_data:
                    row_data = row.strip().split(',')
                    cursor.execute(
                        "INSERT INTO movies (id, title, tagline) VALUES (%s, %s, %s)",
                        (row_data[0], row_data[1], row_data[2])
                    )
            connection.commit()
            logger.info(f"Data from {s3_object_key} has been inserted into RDS.")
            # Send notification to SNS
            sns_client.publish(
                TopicArn=sns_topic_arn,
                Message=f"File {s3_object_key} has been processed and loaded into RDS."
            )
            # Send message to SQS
            sqs_client.send_message(
                QueueUrl=sqs_queue_url,
                MessageBody=f"File {s3_object_key} processed."
            )
    except pymysql.MySQLError as e:
        logger.error(f"MySQL error: {e}")
        raise e
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()
    return {
        'statusCode': 200,
        'body': 'File processed and loaded into RDS successfully'
    }

```
* Enter the above code in space provided in code.
  
  ![preview](images/task23.png)

* Provide a test event by selecting the test which is beside code. Select new event if you want to create an event.
  
  ![preview](images/task24.png)

```json
{
  "Records": [
    {
      "eventSource": "aws:s3",
      "eventName": "ObjectCreated:Put",
      "s3": {
        "object": {
          "key": "example.csv"
        }
      }
    }
  ]
}
```
* In key give the object name that you uploaded in s3 bucket which is a csv file.
  
### 8. Set Environment Variables
1. **Configure Environment Variables for the Lambda Function:**
* **RDS_HOST:** MySQL RDS endpoint.
* **RDS_USER:** MySQL username.
* **RDS_PASSWORD:** MySQL password.
* **RDS_DB_NAME:** MySQL database name.
* **SNS_TOPIC_ARN:** SNS topic ARN.
* **SQS_QUEUE_URL:** SQS queue URL.
  
* Go to lambda function --> configuration --> envitonmental variables --> edit
  
  ![preview](images/task25.png)

### 9. Test the Lambda Functiom
1. Test the code is working are not by clicking the test.
   
   ![preview](images/task26.png)

* you may get error like below because necessary packages for code is needed to make the code run.

```json
{
  "errorMessage": "Unable to import module 'lambda_function': No module named 'pymysql'",
  "errorType": "Runtime.ImportModuleError",
  "requestId": "5b8810fe-861e-4c3b-b217-176db629fda9",
  "stackTrace": []
}
```
* To resolve this issue, you need to ensure that the `pymysql` module is packaged and uploaded with your Lambda function. Here are the steps to do that:

### Step-by-Step Guide to download pysql package
1. **Create a Deployment Package**

* Create an EC2 instance (ubuntu) install pip in that instance.
  
```bash
sudo apt update
sudo apt install python3-pip
sudo apt install zip
```

1. **Install `pymysql` Locally**

* Install `pymysql` in a local directory and zip it along with your Lambda function code.

```bash
mkdir my_lambda_function
cd my_lambda_function
pip install pymysql -t .
```
  
3. **Zip the Contents**

* Zip the contents of the my_lambda_function directory.

```bash
zip -r my_lambda_function.zip .
```
![preview](images/task27.png)

* Now download that zip file from ec2 to local machine using sftp command. 

```
sftp -i "<pemkey>" <username><publicip>
get pymysql-layer.zip .
```
* It will download the file in download's floder.
  
![preview](images/task28.png)
![preview](images/task29.png)

4. **Upload the Deployment Package**

* Go to the AWS Lambda --> layers --> create layer.
  
  ![preview](images/task30.png)

* Now go to the Lambda function you are working with.

![preview](images/task31.png)
![preview](images/task32.png)
![preview](images/task33.png)
![preview](images/task34.png)

### 10. Test the code
* Now run the test and see whether the data is successfully uploaded into RDS by connecting the rds into a mysql workbench.
  
  ![preview](images/task35.png)

### 11. Adding S3 trigger to lambda function
* got to aws lambda console --> functions --> select the function --> add trigger
  
  ![preview](images/task36.png)

* Select S3 and name of the s3 bucket and select event type and add.
*  When the bucket is uploaded with the file then the lambda dunction will trigger and we get the notification.
  
### 12.Check Logs and Outputs:
* Verify the Lambda function execution in CloudWatch logs.
* Check the MySQL database to confirm data insertion.
* Verify SNS notifications and SQS messages.
* If we see the s3 bucket the object modified time.
  ![preview](images/task37.png)

* To see the logs of the lambda function.
  ![preview](images/task38.png)
  ![preview](images/task40.png)
* after completion of the process you will get mail.
  ![preview](images/task39.png)