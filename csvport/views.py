import csv
import requests
import warnings
from django.http import HttpResponse
from django.views import View
import urllib3


class AllocationsCSVView(View):
    def get(self, request):
        reg_no = request.GET.get("reg_no")

        if not reg_no:
            return HttpResponse("Missing 'reg_no' query parameter", status=400)

        # Step 1: API login endpoint
        login_url = "https://portal2.ttu.ac.ke/api/login/"
        credentials = {
            "username": "hostel-checker",
            "password": "rt0[([etx7gvOnSOx4@[CzaAmS][%{"
        }

        # Step 2: Allocations endpoint
        allocations_url = f"https://portal2.ttu.ac.ke/api/allocations/{reg_no}"

        # Bypass SSL warnings
        warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)

        try:
            # Authenticate and get tokens
            auth_res = requests.post(login_url, json=credentials, timeout=10, verify=False)
            auth_res.raise_for_status()
            tokens = auth_res.json()

            if "access" not in tokens:
                return HttpResponse("Authentication failed: no access token returned", status=401)

            access_token = tokens["access"]

            # Fetch allocations using the access token
            headers = {"Authorization": f"Bearer {access_token}"}
            response = requests.get(
                allocations_url,
                headers=headers,
                timeout=10,
                verify=False
            )
            response.raise_for_status()
            data = response.json()

        except requests.RequestException as e:
            return HttpResponse(f"Error fetching data: {e}", status=500)

        if not isinstance(data, list):
            return HttpResponse("Invalid data format from API", status=500)

        # Step 3: Generate CSV response
        response_csv = HttpResponse(content_type="text/csv")
        safe_reg_no = reg_no.replace("/", "_")
        response_csv["Content-Disposition"] = f'attachment; filename="allocations_{safe_reg_no}.csv"'

        writer = csv.writer(response_csv)
        if data:
            headers = data[0].keys()
            writer.writerow(headers)
            for item in data:
                writer.writerow(item.values())
        else:
            writer.writerow(["No data found"])

        return response_csv