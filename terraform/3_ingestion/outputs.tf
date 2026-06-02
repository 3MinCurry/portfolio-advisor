output "vector_bucket_name" {
  description = "Name of the S3 Vectors bucket"
  value       = aws_s3_bucket.vectors.id
}

output "api_endpoint" {
  description = "API Gateway endpoint URL"
  value       = "${aws_api_gateway_stage.api.invoke_url}/ingest"
}

output "api_key_id" {
  description = "API Key ID"
  value       = aws_api_gateway_api_key.api_key.id
}

output "api_key_value" {
  description = "API Key value (sensitive)"
  value       = aws_api_gateway_api_key.api_key.value
  sensitive   = true
}

output "setup_instructions" {
  description = "Post-deploy env hints"
  value       = <<-EOT
    VECTOR_BUCKET=${aws_s3_bucket.vectors.id}
    ALEX_API_ENDPOINT=${aws_api_gateway_stage.api.invoke_url}/ingest
    ALEX_API_KEY=<use api_key_value output or: aws apigateway get-api-key --api-key ${aws_api_gateway_api_key.api_key.id} --include-value --query value --output text>
  EOT
}
