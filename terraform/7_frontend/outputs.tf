output "cloudfront_url" {
  description = "CloudFront distribution URL"
  value       = "https://${aws_cloudfront_distribution.main.domain_name}"
}

output "api_gateway_url" {
  description = "API Gateway URL"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "s3_bucket_name" {
  description = "Name of the S3 bucket for frontend"
  value       = aws_s3_bucket.frontend.id
}

output "lambda_function_name" {
  description = "Name of the API Lambda function"
  value       = aws_lambda_function.api.function_name
}

output "setup_instructions" {
  description = "Post-deploy summary"
  value       = <<-EOT
    CloudFront: https://${aws_cloudfront_distribution.main.domain_name}
    API: ${aws_apigatewayv2_api.main.api_endpoint}
    S3 bucket: ${aws_s3_bucket.frontend.id}
  EOT
}
