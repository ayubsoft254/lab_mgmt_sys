import csv
import requests
from django.http import HttpResponse
from django.views import View
from requests.auth import HTTPBasicAuth


class AllocationsCSVView(View):
    def get(self, request):
        reg_no = request.GET.get("reg_no")

        if not reg_no:
            return HttpResponse("Missing 'reg_no' query parameter", status=400)

        api_url = f"https://portal2.ttu.ac.ke/api/allocations/{reg_no}"
        credentials = {
            "username": "hostel-checker",
            "password": "rt0[([etx7gvOnSOx4@[CzaAmS][%{"
        }

        try:
            # Fetch data with Basic Auth
            response = requests.get(
                api_url,
                auth=HTTPBasicAuth(credentials["username"], credentials["password"]),
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            return HttpResponse(f"Error fetching data: {e}", status=500)

        if not isinstance(data, list):
            return HttpResponse("Invalid data format from API", status=500)

        # Prepare CSV response
        response_csv = HttpResponse(content_type="text/csv")
        response_csv["Content-Disposition"] = f'attachment; filename="allocations_{reg_no}.csv"'

        writer = csv.writer(response_csv)

        if data:
            headers = data[0].keys()
            writer.writerow(headers)
            for item in data:
                writer.writerow(item.values())
        else:
            writer.writerow(["No data found"])

        return response_csv