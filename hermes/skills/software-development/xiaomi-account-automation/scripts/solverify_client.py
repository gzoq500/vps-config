#!/usr/bin/env python3
"""
Solverify.net Captcha Solver API Client
API endpoint: https://solver.solverify.net/ (NOT solverify.net - Cloudflare blocked)
"""
import json, time, urllib.request, urllib.error

BASE_URL = "https://solver.solverify.net"

class SolverifyClient:
    def __init__(self, api_key, base_url=BASE_URL):
        self.api_key = api_key
        self.base_url = base_url

    def _post(self, endpoint, data):
        url = f"{self.base_url}/{endpoint}"
        body = json.dumps({**data, "clientKey": self.api_key}).encode()
        req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            return {"errorId": 1, "errorCode": f"HTTP_{e.code}", "errorDescription": e.read().decode()[:500]}
        except Exception as e:
            return {"errorId": 1, "errorCode": "EXCEPTION", "errorDescription": str(e)}

    def get_balance(self):
        return self._post("getBalance", {})

    def create_task(self, task):
        return self._post("createTask", {"task": task})

    def get_task_result(self, task_id):
        return self._post("getTaskResult", {"taskId": task_id})

    def solve_turnstile(self, website_url, website_key, timeout=120):
        task = {"type": "turnstile", "websiteURL": website_url, "websiteKey": website_key}
        return self._solve(task, timeout)

    def solve_ocr(self, image_base64, timeout=60):
        task = {"type": "ocr", "image": image_base64}
        return self._solve(task, timeout)

    def _solve(self, task, timeout):
        result = self.create_task(task)
        if result.get("errorId", 0) != 0:
            return result
        task_id = result.get("taskId")
        if not task_id:
            return {"errorId": 1, "errorDescription": "No taskId returned"}
        print(f"Task created: {task_id}")
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(5)
            res = self.get_task_result(task_id)
            if res.get("errorId", 0) != 0:
                return res
            status = res.get("status")
            if status == "ready":
                return res
            elif status == "processing":
                print(f"Processing... ({timeout - int(deadline - time.time())}s left)")
            else:
                return {"errorId": 1, "errorDescription": f"Unexpected: {status}"}
        return {"errorId": 1, "errorDescription": f"Timeout after {timeout}s"}

if __name__ == "__main__":
    API_KEY = "YOUR_KEY"
    client = SolverifyClient(API_KEY)
    print(f"Balance: {client.get_balance()}")
