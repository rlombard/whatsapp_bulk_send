# Code Documentation

## WhatsApp Bulk Document Sender - Technical Documentation

### Architecture Overview

The application is structured as a single Python script with clear functional separation:

```
send_whatsapp_upload_and_broadcast.py
├── Imports and Configuration
├── Logging Configuration
├── Environment Management  
├── Utility Functions
├── WhatsApp Cloud API Functions
├── Command Line Argument Parsing
└── Main Application Logic
```

### Key Components

#### 1. Logging System (`setup_logging`)

**Purpose**: Provides comprehensive logging with multiple output options

**Features**:
- Multiple log levels (DEBUG, INFO, WARNING, ERROR)
- Console and file output support
- Timestamp formatting
- Sensitive data masking

**Configuration**:
```python
logger = setup_logging(log_level="INFO", log_file="./logs/app.log")
```

#### 2. Environment Management

**Functions**:
- `load_env_file(path)`: Loads .env files with error handling
- `apply_env(vals)`: Safely applies environment variables

**Security Features**:
- Masks sensitive tokens in logs
- Validates file permissions
- Error handling for missing files

#### 3. Phone Number Processing

**Functions**:
- `sanitize_phone(raw)`: Cleans phone number format
- `validate_phone_number(phone)`: Validates number requirements
- `read_numbers_from_csv(path)`: Processes CSV files with validation

**Validation Rules**:
- Minimum 8 digits for international numbers
- Automatic sanitization (removes non-digits)
- Detailed logging of invalid entries

#### 4. WhatsApp Cloud API Integration

**Core Functions**:
- `upload_media()`: Handles file upload to WhatsApp servers
- `send_template()`: Sends approved message templates
- `send_document_by_id()`: Sends document messages
- `post_json_messages()`: Low-level API communication

**Error Handling**:
- Network timeout management
- API response validation
- Detailed error logging
- Automatic retry logic (future enhancement)

#### 5. Configuration Validation

**Function**: `validate_configuration(config)`

**Validates**:
- Required fields presence
- File existence and permissions
- Numeric value ranges
- Template format compliance
- Path accessibility

### Data Flow

1. **Initialization**
   - Setup logging system
   - Load environment configuration
   - Apply CLI overrides
   - Validate complete configuration

2. **Preparation Phase**
   - Read and validate phone numbers from CSV
   - Check file permissions and sizes
   - Parse template configuration

3. **Media Upload Phase**
   - Upload PDF to WhatsApp Cloud API
   - Receive and validate media ID
   - Handle upload errors gracefully

4. **Broadcasting Phase**
   - Iterate through recipient list
   - Send template message (if configured)
   - Send document message
   - Apply rate limiting
   - Track success/failure statistics

5. **Completion**
   - Generate final statistics
   - Log operation summary
   - Exit with appropriate status code

### Configuration Hierarchy

The application uses a three-tier configuration system:

1. **Environment Variables** (lowest priority)
2. **`.env` File** (medium priority)
3. **Command Line Arguments** (highest priority)

### Error Handling Strategy

#### Validation Errors
- Caught early in configuration validation
- Clear error messages with resolution guidance
- Prevents API calls with invalid configuration

#### Network Errors
- Timeout handling for API requests
- Detailed logging of request/response data
- Graceful degradation for individual failures

#### File System Errors
- Permission checking before operations
- Clear error messages for missing files
- Path validation and normalization

### Security Considerations

#### Data Protection
- Access tokens masked in logs (`token[:10]...`)
- Phone numbers partially masked in logs
- No sensitive data in debug output

#### File Security
- Validates file permissions before reading
- Creates directories with appropriate permissions
- Temporary file cleanup (if implemented)

#### API Security  
- Validates API responses before processing
- Timeout protection against hanging requests
- Rate limiting to respect API constraints

### Logging Levels Guide

#### DEBUG Level
- Environment variable loading details
- Phone number processing steps
- API request/response headers and payloads
- File system operations
- Rate limiting delays

#### INFO Level (Default)
- Operation phases and progress
- Configuration summary (sensitive data masked)
- Success/failure for each recipient
- Final statistics and timing

#### WARNING Level
- Invalid phone numbers (with reasons)
- Non-critical configuration issues
- Recovery from minor errors
- Performance warnings

#### ERROR Level
- Configuration validation failures
- API communication errors
- File system errors
- Fatal errors preventing operation

### Performance Considerations

#### Memory Usage
- Streams large files instead of loading entirely
- Processes phone numbers incrementally
- Limited log buffer sizes

#### Network Efficiency
- Reuses HTTP connections where possible
- Implements appropriate timeouts
- Rate limiting prevents API abuse

#### File System
- Validates paths before operations
- Uses appropriate file encodings
- Handles large CSV files efficiently

### Extension Points

The code is designed for easy extension:

#### New Message Types
- Add new functions following `send_document_by_id` pattern
- Extend payload generation
- Update configuration validation

#### Additional File Formats
- Extend MIME type detection
- Add format-specific validation
- Update upload logic if needed

#### Enhanced Rate Limiting
- Implement exponential backoff
- Add retry logic with delays
- Respect API quota limits

#### Metrics and Monitoring
- Add performance timing
- Implement success rate tracking
- Export metrics in standard formats

### Testing Strategy

#### Unit Tests (Recommended additions)
- Configuration validation functions
- Phone number processing
- Environment loading
- Utility functions

#### Integration Tests
- API communication with test credentials
- File processing with sample data
- End-to-end workflow validation

#### Manual Testing
- Use `--dry-run` for safe testing
- Test with single recipient first
- Validate with DEBUG logging enabled

---

## Code Quality Standards

### Documentation
- All functions have comprehensive docstrings
- Type hints for parameters and return values
- Inline comments for complex logic
- Usage examples in docstrings

### Error Messages
- Specific and actionable error descriptions
- Include relevant context (file paths, values)
- Suggest resolution steps where possible
- Log at appropriate levels

### Code Organization
- Clear functional separation
- Logical grouping of related functions
- Consistent naming conventions
- Minimal code duplication

---

**Last Updated**: 2025-10-20  
**Version**: 2.0.0