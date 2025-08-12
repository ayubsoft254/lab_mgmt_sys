from django.shortcuts import render
import csv
import requests
from django.http import HttpResponse
from django.views import View


class AllocationsCSVView(View):
    def get(self, request):
        # Step 1: Fetch the JSON data from the API
        api_url = "https://portal2.ttu.ac.ke/api/allocations/"
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.RequestException as e:
            return HttpResponse(f"Error fetching data: {e}", status=500)

        # Ensure data is a list of dictionaries
        if not isinstance(data, list):
            return HttpResponse("Invalid data format from API", status=500)

        # Step 2: Create HTTP response for CSV
        response_csv = HttpResponse(content_type="text/csv")
        response_csv["Content-Disposition"] = 'attachment; filename="allocations.csv"'

        # Step 3: Write CSV header & rows
        writer = csv.writer(response_csv)

        if data:
            # Extract headers from keys of the first dictionary
            headers = data[0].keys()
            writer.writerow(headers)

            # Write each row
            for item in data:
                writer.writerow(item.values())
        else:
            writer.writerow(["No data found"])

        return response_csv
