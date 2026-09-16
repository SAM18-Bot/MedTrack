import boto3
import argparse

def set_parameter(name, value, ptype="SecureString"):
    ssm = boto3.client('ssm')
    ssm.put_parameter(
        Name=f"/medtrack/prod/{name}",
        Description=f"MedTrack Prod Parameter: {name}",
        Value=value,
        Type=ptype,
        Overwrite=True
    )
    print(f"Set parameter: /medtrack/prod/{name}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Configure AWS Systems Manager Parameter Store for MedTrack")
    parser.add_argument("--secret-key", help="Flask SECRET_KEY")
    parser.add_argument("--s3-bucket", help="S3 Bucket Name")
    args = parser.parse_args()

    if args.secret_key:
        set_parameter("SECRET_KEY", args.secret_key)
    if args.s3_bucket:
        set_parameter("S3_BUCKET_NAME", args.s3_bucket, "String")
    
    if not args.secret_key and not args.s3_bucket:
        print("Usage: python setup_ssm.py --secret-key <key> --s3-bucket <bucket>")
