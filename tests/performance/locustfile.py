import random
import logging
from locust import HttpUser, SequentialTaskSet, task, between, LoadTestShape

logging.basicConfig(level=logging.INFO)

class UserBehavior(SequentialTaskSet):
    """
    Automated user lifecycle.
    Define your task sequence here.
    """
    def on_start(self):
        """Initialization for each virtual user."""
        self.user_id = random.randint(1000, 9999)
        logging.info(f"Starting session for user {self.user_id}")

    @task
    def phase_1_explore(self):
        """Consulta la página de inicio."""
        with self.client.get("/", catch_response=True, name="1. GET / (Home)") as response:
            if response.status_code in [200, 304]:
                response.success()
            else:
                response.failure(f"Error cargando Home con status: {response.status_code}")

    @task
    def phase_2_get_businesses(self):
        """Consulta el listado público de negocios (solo lectura, sin creación de datos)."""
        with self.client.get("/businesses/", catch_response=True, name="2. GET /businesses/") as response:
            if response.status_code in [200, 304]:
                response.success()
            else:
                response.failure(f"Error consultando /businesses/ con status: {response.status_code}")

    @task
    def finish_lifecycle(self):
        """Stops the task execution for this user."""
        self.interrupt()

class ApiLoadTester(HttpUser):
    tasks = [UserBehavior]
    wait_time = between(1, 4) 

# ==========================================
# 🚦 AUTOMATED TRAFFIC CONTROLLER (STAGES)
# ==========================================
class AutomatedTrafficShape(LoadTestShape):
    """
    Simulates a realistic traffic pattern with stages.
    """
    stages = [
        {"duration": 10, "users": 5, "spawn_rate": 2},    # Stage 1: Warmup
        {"duration": 20, "users": 10, "spawn_rate": 5},   # Stage 2: Peak
        {"duration": 30, "users": 2, "spawn_rate": 2},    # Stage 3: Cooldown
    ]

    def tick(self):
        run_time = self.get_run_time()

        for stage in self.stages:
            if run_time < stage["duration"]:
                tick_data = (stage["users"], stage["spawn_rate"])
                return tick_data

        return None # Stop test automatically when stages end