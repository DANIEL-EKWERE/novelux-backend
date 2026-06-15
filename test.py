# import boto3
# import os
# from dotenv import load_dotenv
# import mimetypes

# load_dotenv()

# AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
# AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
# AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')

# def upload_to_s3(file_path, bucket_name):
#     s3 = boto3.client(
#         's3',
#         aws_access_key_id=AWS_ACCESS_KEY_ID,
#         aws_scret_access_key=AWS_SECRET_ACCESS_KEY,
#     )
#     file_name = os.path.basename(file_name)
#     content_type,_= mimetypes.guess_type(file_path)

#     if content_type is None:
#         content_type = 'application/octet-stream'

#     with open(file_path, 'rb') as file:

#         s3.upload_fileobj(file, bucket_name, file_name, ExtraArgs={
#             'ContentType': content_type
#         })

#     bucket_location = s3.get_bucket_location(Bucket=bucket_name)
#     region = bucket_location['LocationConstraint'] if bucket_location['LocationConstraint'] else 'eu-north-1'
#     file_url = f"https://{bucket_name}.s3.{region}.amazon.com/{file_name.replace('','+')}"
#     return file_url
# # file_url = f"https://s3.{region}.amazon.com/{bucket_name}/{file_name.replace('','+')}"
# # https://novelux-bucket.s3.eu-north-1.amazonaws.com/1024.png    

# def main():
#     file_path = 'seven.jpg'
#     file_url = upload_to_s3(file_path, AWS_STORAGE_BUCKET_NAME)
#     print(f"File upload successfully, Access it at: {file_url}")

# if __name__ == '__main__':
#     main()


import boto3
import os
from dotenv import load_dotenv
import mimetypes

load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY')
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_STORAGE_BUCKET_NAME')

def upload_to_s3(file_path, bucket_name):
    s3 = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        # FIXED TYPO: changed 'aws_scret_access_key' to 'aws_secret_access_key'
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    
    # FIXED VARIABLE: You were using file_name before defining it
    file_name = os.path.basename(file_path) 
    content_type, _ = mimetypes.guess_type(file_path)

    if content_type is None:
        content_type = 'application/octet-stream'

    with open(file_path, 'rb') as file:
        s3.upload_fileobj(file, bucket_name, file_name, ExtraArgs={
            'ContentType': content_type
        })

    bucket_location = s3.get_bucket_location(Bucket=bucket_name)
    region = bucket_location['LocationConstraint'] if bucket_location['LocationConstraint'] else 'us-east-1'
    
    # FIXED URL: The standard S3 URL format is bucket.s3.region.amazonaws.com
    file_url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{file_name}"
    return file_url

def main():
    file_path = 'seven.jpg'
    # Ensure this file actually exists in your folder!
    if not os.path.exists(file_path):
        print(f"Error: The file '{file_path}' was not found in this directory.")
        return
        
    file_url = upload_to_s3(file_path, AWS_STORAGE_BUCKET_NAME)
    print(f"File uploaded successfully! Access it at: {file_url}")

# FIXED: Changed '__name__' to '__main__'
if __name__ == '__main__':
    main()

'''

'''    