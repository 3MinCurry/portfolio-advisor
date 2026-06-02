output "sqs_queue_url" {
  description = "URL of the SQS queue for job submission"
  value       = aws_sqs_queue.analysis_jobs.url
}

output "sqs_queue_arn" {
  description = "ARN of the SQS queue"
  value       = aws_sqs_queue.analysis_jobs.arn
}

output "lambda_functions" {
  description = "Names of deployed Lambda functions"
  value = {
    planner    = aws_lambda_function.planner.function_name
    tagger     = aws_lambda_function.tagger.function_name
    reporter   = aws_lambda_function.reporter.function_name
    charter    = aws_lambda_function.charter.function_name
    retirement = aws_lambda_function.retirement.function_name
    risk       = aws_lambda_function.risk.function_name
  }
}

output "setup_instructions" {
  description = "Post-deploy summary"
  value       = "Agent Lambdas and SQS deployed. Set SQS_QUEUE_URL=${aws_sqs_queue.analysis_jobs.url} in .env"
}
