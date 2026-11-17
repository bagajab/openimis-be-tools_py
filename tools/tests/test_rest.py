
from unittest import mock

from core.test_helpers import create_test_interactive_user
from tablib import Dataset
from rest_framework import status
from rest_framework.test import APITestCase
from graphql_jwt.shortcuts import get_token
from django.conf import settings
import os
from django.core.files.uploadedfile import SimpleUploadedFile
from core.models.openimis_graphql_test_case import BaseTestContext as DummyContext


class ReportAPITests(APITestCase):

    admin_user = None
    admin_token = None
    dir_path = None

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.admin_user = create_test_interactive_user(username="testLocationAdmin")
        cls.admin_token = get_token(cls.admin_user, DummyContext(user=cls.admin_user))
        cls.dir_path = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

    def test_import_item_json(self):
        URL = f'/{settings.SITE_ROOT()}tools/imports/items?file_format=json'
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}
        with open(os.path.join(self.dir_path, 'tests/item_example.json'), 'rb') as f:
            file_content = f.read()
            uploaded_file = SimpleUploadedFile("service_example.json", file_content, content_type="application/json")
            response = self.client.post(URL, {'file': uploaded_file}, format='multipart', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_export_item_xls(self):
        URL = f'/{settings.SITE_ROOT()}tools/exports/items?file_format=xls'
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}
        response = self.client.get(URL, format='json', **headers)

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_import_service_json(self):
        URL = f'/{settings.SITE_ROOT()}tools/imports/services?file_format=json'
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}
        with open(os.path.join(self.dir_path, 'tests/service_example.json'), 'rb') as f:
            file_content = f.read()
            uploaded_file = SimpleUploadedFile("service_example.json", file_content, content_type="application/json")
            response = self.client.post(URL, {'file': uploaded_file}, format='multipart', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def test_export_service_xls(self):
        URL = f'/{settings.SITE_ROOT()}tools/exports/services?file_format=xls'
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}
        response = self.client.get(URL, format='json', **headers)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

    def _export(self, register, file_format):
        URL = f'/{settings.SITE_ROOT()}tools/exports/{register}?file_format={file_format}'
        headers = {"HTTP_AUTHORIZATION": f"Bearer {self.admin_token}"}
        return self.client.get(URL, format='json', **headers)

    def test_export_items_and_services_in_every_supported_format(self):
        # xls and xlsx need tablib's optional extras (xlwt, openpyxl): the
        # module must declare them, or a plain pip install exports nothing.
        expected = {
            "xls": "application/vnd.ms-excel",
            "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "csv": "text/csv",
            "json": "application/json",
        }
        for register in ("items", "services"):
            for file_format, content_type in expected.items():
                with self.subTest(register=register, file_format=file_format):
                    response = self._export(register, file_format)
                    self.assertEqual(response.status_code, status.HTTP_200_OK, response.content[:500])
                    self.assertEqual(response["Content-Type"], content_type)
                    self.assertIn(f'filename="{register}.{file_format}"', response["Content-Disposition"])

    def test_export_csv_does_not_render_other_formats(self):
        # The export used to render every format and keep one, so a missing
        # xlsx backend broke the CSV export as well.
        def unavailable(_dataset):
            raise AttributeError("'Dataset' object has no attribute 'xlsx'")

        with mock.patch.object(Dataset, "xlsx", property(unavailable)), \
                mock.patch.object(Dataset, "xls", property(unavailable)):
            for register in ("items", "services"):
                with self.subTest(register=register):
                    response = self._export(register, "csv")
                    self.assertEqual(response.status_code, status.HTTP_200_OK, response.content[:500])
