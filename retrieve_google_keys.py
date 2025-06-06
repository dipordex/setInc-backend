from os import environ

import boto3
from botocore.exceptions import ClientError


def get_secret(secret_name: str) -> str:
    session = boto3.session.Session(
        aws_access_key_id=environ.get('ASM_AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=environ.get('ASM_AWS_SECRET_ACCESS_KEY'),
    )

    client = session.client(
        service_name='secretsmanager',
        region_name=environ.get('AWS_SECRET_REGION_NAME')
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    # Decrypts secret using the associated KMS key.
    if 'SecretString' in get_secret_value_response:
        return get_secret_value_response['SecretString']
    else:
        print(f'Error retrieving key: {get_secret_value_response}')


def main(keys: dict) -> None:
    """ Retrieve keys from AWS & save """
    for key, filename in keys.items():  # Use .items() instead of .values()
        secret = get_secret(key)
        # Change in case of multiple files will need to be parsed
        with open(filename, 'w') as f:
            f.write(secret)
            print(f'Successfully created {filename}!')


if __name__ == "__main__":
    service_keys = {
        'setinc_google_api_prod': './google-services.json',
        'setinc_firebase': './firebase.json',
    }
    main(service_keys)
