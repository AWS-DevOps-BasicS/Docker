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
        cursor.execute("truncate table movies")
        # Ensure the table exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS movies (
                id INT,
                title VARCHAR(100),
                tagline VARCHAR(100)
            )
        """)
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