# Logs directory
This directory contains application logs and runtime information.

## Log Files

- `app.log` - Main application log file with structured logging
- Runtime logs are automatically rotated and managed by the application

## Log Configuration

The application uses Python's built-in logging with the following configuration:
- Level: INFO
- Format: Timestamp - Logger - Level - [File:Line] - Message
- Handlers: Console and file output

## Log Retention

Logs are kept for debugging and monitoring purposes. In production environments, consider implementing log rotation and retention policies.
