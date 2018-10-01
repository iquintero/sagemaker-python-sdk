# Copyright 2017-2018 Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"). You
# may not use this file except in compliance with the License. A copy of
# the License is located at
#
#     http://aws.amazon.com/apache2.0/
#
# or in the "license" file accompanying this file. This file is
# distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF
# ANY KIND, either express or implied. See the License for the specific
# language governing permissions and limitations under the License.
from __future__ import absolute_import

import os
import pytest
from mock import call, patch, Mock

import sagemaker

BUCKET_NAME = 'some-nice-bucket'


@patch('os.makedirs')
def test_download_folder(makedirs):
    boto_mock = Mock(name='boto_session')
    boto_mock.client('sts').get_caller_identity.return_value = {'Account': '123'}

    session = sagemaker.Session(boto_session=boto_mock, sagemaker_client=Mock())

    train_data = Mock()
    validation_data = Mock()

    train_data.bucket_name.return_value = BUCKET_NAME
    train_data.key = 'prefix/train/train_data.csv'
    validation_data.bucket_name.return_value = BUCKET_NAME
    validation_data.key = 'prefix/train/validation_data.csv'

    s3_files = [train_data, validation_data]
    boto_mock.resource('s3').Bucket(BUCKET_NAME).objects.filter.return_value = s3_files

    obj_mock = Mock()
    boto_mock.resource('s3').Object.return_value = obj_mock

    sagemaker.local.utils.download_folder(BUCKET_NAME, '/prefix', '/tmp', session)

    obj_mock.download_file.assert_called()
    calls = [call(os.path.join('/tmp', 'train/train_data.csv')),
             call(os.path.join('/tmp', 'train/validation_data.csv'))]
    obj_mock.download_file.assert_has_calls(calls)
    obj_mock.reset_mock()

    # Testing with a trailing slash for the prefix.
    sagemaker.local.utils.download_folder(BUCKET_NAME, '/prefix/', '/tmp', session)
    obj_mock.download_file.assert_called()
    calls = [call(os.path.join('/tmp', 'train/train_data.csv')),
             call(os.path.join('/tmp', 'train/validation_data.csv'))]

    obj_mock.download_file.assert_has_calls(calls)


def test_download_file():
    boto_mock = Mock(name='boto_session')
    boto_mock.client('sts').get_caller_identity.return_value = {'Account': '123'}
    bucket_mock = Mock()
    boto_mock.resource('s3').Bucket.return_value = bucket_mock
    session = sagemaker.Session(boto_session=boto_mock, sagemaker_client=Mock())

    sagemaker.local.utils.download_file(BUCKET_NAME, '/prefix/path/file.tar.gz',
                                        '/tmp/file.tar.gz', session)

    bucket_mock.download_file.assert_called_with('prefix/path/file.tar.gz', '/tmp/file.tar.gz')


@patch('shutil.rmtree', Mock())
@patch('sagemaker.local.utils.recursive_copy')
def test_move_to_destination(recursive_copy):
    # local files will just be recursive copied
    sagemaker.local.utils.move_to_destination('/tmp/data', 'file:///target/dir/', None)
    recursive_copy.assert_called()

    # s3 destination will upload to S3
    sms = Mock()
    sagemaker.local.utils.move_to_destination('/tmp/data', 's3://bucket/path', sms)
    sms.upload_data.assert_called()

    # weird destination, should raise an exception
    with pytest.raises(ValueError):
        sagemaker.local.utils.move_to_destination('/tmp/data', 'ftp://ftp/in/2018', None)
