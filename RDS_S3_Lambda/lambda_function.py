import json
import boto3
import pymysql
import os
import logging
import csv  # Import the csv module

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


sns_client = boto3.client('sns')
sqs_client = boto3.client('sqs')

# Environment variables
rds_host = os.environ['RDS_HOST']
db_username = os.environ['DB_USERNAME']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
table_name = os.environ['TABLE_NAME']
sns_topic_arn = os.environ['SNS_TOPIC_ARN']
sqs_queue_url = os.environ['SQS_QUEUE_URL']

# Initialize S3 client
s3 = boto3.client('s3')
def lambda_handler(event, context):
    if 'Records' not in event:
        raise ValueError("No 'Records' found in event")
    
    for record in event['Records']:
        try:
            bucket = record['s3']['bucket']['name']
            key = record['s3']['object']['key']
            
            # Download file from S3
            local_file_path = '/tmp/movies_complete.csv'
            s3.download_file(bucket, key, local_file_path)
            
            # Connect to RDS
            conn = pymysql.connect(host=rds_host,
                                   user=db_username,
                                   password=db_password,
                                   database=db_name)
            cursor = conn.cursor()
            cursor.execute("truncate table movies")
            # Insert data into RDS
            with open(local_file_path, 'r') as file:
                csv_data = csv.reader(file)
                next(csv_data)  # Skip header row
                for row in csv_data:
                    row=row[0:3]
                    print(f"Inserting row: {row}")  # Debugging: print the row
                    cursor.execute("INSERT INTO {} (id, names, tagline) VALUES (%s, %s, %s)".format(table_name), row)
            
            # Commit changes and close connection
            conn.commit()
            cursor.close()
            conn.close()
            
            # Log successful processing
            print(f"Successfully processed file {key} from bucket {bucket}")
        
        except Exception as e:
            print(f"Error processing file {key} from bucket {bucket}: {e}")
            raise e
    
    return {
        'statusCode': 200,
        'body': json.dumps('Data loaded successfully')
    }
