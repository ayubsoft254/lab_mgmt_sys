import csv
import requests
import warnings
from django.http import HttpResponse
from django.views import View
import urllib3


class AllocationCSVView(View):
    def get(self, request):
        reg_no = request.GET.get("reg_no")
        if not reg_no:
            return HttpResponse("Missing 'reg_no' query parameter", status=400)

        API_BASE = "https://portal2.ttu.ac.ke"
        token_url = f"{API_BASE}/api/token/"
        data_url = f"{API_BASE}/api/allocation/?reg_no={reg_no}"

        credentials = {
            "username": "hostel-checker",
            "password": "rt0[([etx7gvOnSOx4@[CzaAmS][%{"
        }

        warnings.simplefilter("ignore", urllib3.exceptions.InsecureRequestWarning)

        try:
            # Step 1: Get access token
            token_res = requests.post(token_url, json=credentials, verify=False, timeout=10)
            token_res.raise_for_status()
            tokens = token_res.json()

            if "access" not in tokens:
                return HttpResponse(f"Authentication failed: {tokens}", status=401)

            access_token = tokens["access"]

            # Step 2: Fetch allocation data
            headers = {"Authorization": f"Bearer {access_token}"}
            data_res = requests.get(data_url, headers=headers, verify=False, timeout=10)
            data_res.raise_for_status()
            data = data_res.json()

        except requests.RequestException as e:
            return HttpResponse(f"Error fetching data: {e}", status=500)

        # Step 3: Handle different data shapes
        if not data:
            return HttpResponse("No data returned", status=404)

        # If data is wrapped inside another key like {"results": [...]}
        if isinstance(data, dict):
            # Try common patterns
            if "results" in data and isinstance(data["results"], list):
                data = data["results"]
            elif "data" in data and isinstance(data["data"], list):
                data = data["data"]
            else:
                # Convert dict to a list for CSV export
                data = [data]

        if not isinstance(data, list) or not data:
            return HttpResponse("Data format not supported for CSV export", status=500)

        # Step 4: Create CSV response
        response_csv = HttpResponse(content_type="text/csv")
        safe_reg_no = reg_no.replace("/", "_").replace(" ", "_")
        response_csv["Content-Disposition"] = f'attachment; filename="allocation_{safe_reg_no}.csv"'

        writer = csv.writer(response_csv)

        # Use consistent headers
        headers_list = list(data[0].keys())
        writer.writerow(headers_list)

        for item in data:
            row = [item.get(h, "") for h in headers_list]
            writer.writerow(row)

        return response_csv