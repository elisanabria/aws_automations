# 🚀 AWS Automations

**A library of AWS automation scripts built for Security in multi-account infrastructures.**  
Modular, extensible, and production-ready — these automations are intended for helping with some Use Cases I've found in my not-that-awesome but curious and enthusiastic path in the AWS Cloud Security area.

---

## 📁 Automation Library

Each folder contains a standalone automation focused on a specific AWS Security use case.

| Automation | Description |
|------------|-------------|
| [`analytics-reports`](./analytics_reports) | Scheduled report based on Athena and CloudWatch queries execution + IAM Identity Center User inventory. |
| [`cloudtrail-activity-alerts`](./cloudtrail_activity_alerts) | Real-time alerts for sensitive CloudTrail events with centralized Lambda processing. |
| [`ephemeral-resources-lifecycle`](./ephemeral_resources_lifecycle) | Monitors EC2 & RDS tagged as `Ephemeral=True` and triggers alerts after 30 days. |


> ⚙️ Each folder includes:
> - 📄 CloudFormation templates  
> - 🐍 Python code for Lambda functions  
> - 🧪 Optional test files or helper scripts  

---

## 🌍 Architecture Principles

- ✅ Built for **multi-account** AWS Organizations
- 📦 Delivered as **CloudFormation-first** automations
- 🔐 Prioritize **Security**, **Auditability**, and **Least Privilege**
- 🧩 Easy to integrate with existing pipelines (CI/CD, DevSecOps)

---

## 🧭 Getting Started

Each folder has a README with their corresponding instructions.

---

## 🔮 Made with love, caffeine, sugar and much much love for automagic.
