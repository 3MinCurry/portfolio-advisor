output "ecr_repository_url" {
  description = "URL of the ECR repository"
  value       = aws_ecr_repository.researcher.repository_url
}

output "researcher_url" {
  description = "Public HTTPS URL of the researcher Lambda"
  value       = try(aws_lambda_function_url.researcher[0].function_url, "Not created yet - run deploy.py")
}

output "researcher_function_name" {
  description = "Name of the researcher Lambda function"
  value       = try(aws_lambda_function.researcher[0].function_name, "Not created yet")
}

output "scheduler_status" {
  description = "Status of the automated scheduler"
  value = !local.researcher_deployed ? "Disabled - deploy the researcher image first" : (
    var.scheduler_enabled ? "Enabled - every 2 hours" : "Disabled"
  )
}

output "setup_instructions" {
  description = "Post-deploy summary"
  value = local.researcher_deployed ? (
    "Researcher URL: ${aws_lambda_function_url.researcher[0].function_url}"
  ) : "Run backend/researcher/deploy.py to build and deploy the researcher image."
}
