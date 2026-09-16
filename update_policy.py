import json
import re

with open('scripts/create_tables.py', 'r') as f:
    content = f.read()

# Extract tables and their indexes
tables = []
current_table = None
import ast

# Just parse with regex to be safe
table_matches = re.findall(r'"TableName": f"{prefix}(\w+)"', content)
table_indexes = {t: [] for t in table_matches}

# a hacky parsing
blocks = content.split('"TableName": f"{prefix}')
for block in blocks[1:]:
    table_name = block.split('"')[0]
    index_matches = re.findall(r'"IndexName": "([^"]+)"', block)
    for idx in index_matches:
        table_indexes[table_name].append(idx)

resources = []
for table, indexes in table_indexes.items():
    resources.append(f"arn:aws:dynamodb:us-east-1:111122223333:table/MedTrack-{table}")
    for idx in set(indexes):
        resources.append(f"arn:aws:dynamodb:us-east-1:111122223333:table/MedTrack-{table}/index/{idx}")

with open('iam/ec2_instance_profile.json', 'r') as f:
    policy = json.load(f)

for statement in policy['Statement']:
    if statement['Action'] == ['dynamodb:PutItem', 'dynamodb:GetItem', 'dynamodb:Scan', 'dynamodb:Query', 'dynamodb:UpdateItem', 'dynamodb:DeleteItem', 'dynamodb:TransactWriteItems']:
        statement['Resource'] = resources

with open('iam/ec2_instance_profile.json', 'w') as f:
    json.dump(policy, f, indent=4)
