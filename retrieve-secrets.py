#!/usr/bin/env python

import argparse
import json
import shutil

import boto3
import base64
from botocore.exceptions import ClientError
from os import environ


def get_secrets():
    secret_name = environ.get('AWS_SECRET_NAME')
    region_name = environ.get('AWS_SECRET_REGION_NAME')

    session = boto3.session.Session(
        aws_access_key_id=environ.get('ASM_AWS_ACCESS_KEY_ID'),
        aws_secret_access_key=environ.get('ASM_AWS_SECRET_ACCESS_KEY'),
    )

    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        print(f'Loading secret "{secret_name}" from AWS...')
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    # except Exception as e:
    #     print(e)
    except ClientError as e:
        if e.response['Error']['Code'] == 'DecryptionFailureException':
            # Secrets Manager can't decrypt the protected secret text using the provided KMS key.
            # Deal with the exception here, and/or rethrow at your discretion.
            print(e)
            # raise e
        elif e.response['Error']['Code'] == 'InternalServiceErrorException':
            # An error occurred on the server side.
            # Deal with the exception here, and/or rethrow at your discretion.
            print(e)
            # raise e
        elif e.response['Error']['Code'] == 'InvalidParameterException':
            # You provided an invalid value for a parameter.
            # Deal with the exception here, and/or rethrow at your discretion.
            print(e)
            # raise e
        elif e.response['Error']['Code'] == 'InvalidRequestException':
            # You provided a parameter value that is not valid for the current state of the resource.
            # Deal with the exception here, and/or rethrow at your discretion.
            print(e)
            # raise e
        elif e.response['Error']['Code'] == 'ResourceNotFoundException':
            # We can't find the resource that you asked for.
            # Deal with the exception here, and/or rethrow at your discretion.
            print(e)
            # raise e
        raise e
    else:
        # Decrypts secret using the associated KMS CMK.
        # Depending on whether the secret is a string or binary, one of these fields will be populated.
        print(f'Successfully loaded secrets from AWS!')
        if 'SecretString' in get_secret_value_response:
            secret = get_secret_value_response['SecretString']
            return True, secret
        else:
            decoded_binary_secret = base64.b64decode(get_secret_value_response['SecretBinary'])
            return False, decoded_binary_secret


def parse_secret(secret_name):
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
        # For a list of exceptions thrown, see
        # https://docs.aws.amazon.com/secretsmanager/latest/apireference/API_GetSecretValue.html
        raise e

    # Decrypts secret using the associated KMS key.
    return get_secret_value_response['SecretString']


def main(filename):
    """Retrieve secrets from AWS & save as .env file."""

    is_string, secrets = get_secrets()

    if is_string:
        secrets_json = json.loads(secrets)

        file_contents = ''
        for k, v in secrets_json.items():
            value = str(v).lower() if type(v) is bool else v
            file_contents += f'{k}={value}\n'

        with open(filename, 'w') as f:
            f.write(file_contents)
            print(f'Successfully created {filename}!')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Retrieve secrets from AWS & save as .env file.')
    parser.add_argument('output', metavar='output', default='.aws-secrets.env', nargs=1,
                        help='output .env file name')
    args = parser.parse_args()
    filename = args.output[0]

    main(filename)

    # Move to single file
    # key = 'setinc_google_api_prod'
    # firebase_cred = parse_secret(key)
    # filename = f'./.deploy/google-services.json'
    # with open(filename, 'w') as f:
    #     f.write(firebase_cred)
    #     print(f'Successfully created {filename}!')
