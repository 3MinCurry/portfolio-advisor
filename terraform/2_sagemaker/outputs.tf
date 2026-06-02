
output "sagemaker_endpoint_name" {
  description = "Name of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.embedding_endpoint.name
}

output "sagemaker_endpoint_arn" {
  description = "ARN of the SageMaker endpoint"
  value       = aws_sagemaker_endpoint.embedding_endpoint.arn
}

output "setup_instructions" {
  description = "Post-deploy env hint"
  value       = "SageMaker endpoint deployed. Set SAGEMAKER_ENDPOINT=${aws_sagemaker_endpoint.embedding_endpoint.name} in .env"
}
