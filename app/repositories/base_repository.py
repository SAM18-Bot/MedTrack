import os
import time
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class BaseRepository:
    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        )
        self.table_prefix = os.environ.get('DYNAMODB_PREFIX', 'MedTrack-')

    def _get_table(self, table_name):
        return self.dynamodb.Table(f"{self.table_prefix}{table_name}")

    def _execute_with_retry(self, operation, *args, **kwargs):
        max_retries = 3
        base_delay = 0.5
        for attempt in range(max_retries):
            try:
                return operation(*args, **kwargs)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException']:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries reached for {error_code}.")
                        raise ValueError("Service is currently busy. Please try again later.")
                    time.sleep(base_delay * (2 ** attempt))
                else:
                    logger.error(f"DynamoDB ClientError: {error_code} - {str(e)}")
                    raise ValueError(f"Database operation failed: {error_code}")
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                raise ValueError("An unexpected error occurred.")

    def get_item(self, table_name, key):
        table = self._get_table(table_name)
        response = self._execute_with_retry(table.get_item, Key=key)
        item = response.get('Item')
        if not item:
            return None
        if item.get('IsDeleted'):
            return None
        return item

    def put_item(self, table_name, item, condition_expression=None):
        table = self._get_table(table_name)
        kwargs = {'Item': item}
        if condition_expression:
            kwargs['ConditionExpression'] = condition_expression
        self._execute_with_retry(table.put_item, **kwargs)
        return item

    def update_item(self, table_name, key, update_expression, expression_attribute_values, expression_attribute_names=None):
        table = self._get_table(table_name)
        kwargs = {
            'Key': key,
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_attribute_values,
            'ReturnValues': 'ALL_NEW'
        }
        if expression_attribute_names:
            kwargs['ExpressionAttributeNames'] = expression_attribute_names
        response = self._execute_with_retry(table.update_item, **kwargs)
        return response.get('Attributes')

    def query_index(self, table_name, index_name, key_condition_expression, expression_attribute_values):
        table = self._get_table(table_name)
        response = self._execute_with_retry(
            table.query,
            IndexName=index_name,
            KeyConditionExpression=key_condition_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        items = response.get('Items', [])
        return [item for item in items if not item.get('IsDeleted')]

    def soft_delete(self, table_name, key):
        from app.utils import get_utc_now
        return self.update_item(
            table_name=table_name,
            key=key,
            update_expression="SET IsDeleted = :val, UpdatedAt = :updated",
            expression_attribute_values={
                ':val': True,
                ':updated': get_utc_now()
            }
        )
