"""
Script to apply Sentry decorators to service files
"""
import os
import re

def add_sentry_import(content, import_statement):
    """Add Sentry import to file if not already present"""
    if import_statement not in content:
        # Find the last import statement
        import_section_end = 0
        for match in re.finditer(r'^from|^import', content, re.MULTILINE):
            line_end = content.find('\n', match.start())
            if line_end > import_section_end:
                import_section_end = line_end
        
        # Insert the import after the last import
        if import_section_end > 0:
            return content[:import_section_end + 1] + import_statement + content[import_section_end + 1:]
    
    return content

def add_decorators_to_functions(content, decorator):
    """Add decorator to all function definitions"""
    # Pattern to match function definitions
    pattern = r'^def\s+([a-zA-Z0-9_]+)\s*\('
    
    # Find all function definitions
    matches = list(re.finditer(pattern, content, re.MULTILINE))
    
    # Add decorators from bottom to top to avoid changing positions
    for match in reversed(matches):
        # Check if function already has the decorator
        line_start = content.rfind('\n', 0, match.start()) + 1
        if line_start > 0:
            prev_line = content[content.rfind('\n', 0, line_start - 1) + 1:line_start - 1]
            if decorator in prev_line:
                continue
        
        # Add decorator before function definition
        content = content[:line_start] + decorator + '\n' + content[line_start:]
    
    return content

def process_file(file_path, decorator, import_statement):
    """Process a file to add Sentry decorators"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Add import if needed
    content = add_sentry_import(content, import_statement)
    
    # Add decorators to functions
    content = add_decorators_to_functions(content, decorator)
    
    # Write back to file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"Processed {file_path}")

def main():
    """Main function"""
    # Define the decorator and import statement
    decorator = "@sentry_monitored_service"
    import_statement = "from app.utils.sentry import sentry_monitored_service\n"
    
    # Process service files
    service_dir = os.path.join('app', 'services')
    for filename in os.listdir(service_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            file_path = os.path.join(service_dir, filename)
            process_file(file_path, decorator, import_statement)

if __name__ == "__main__":
    main()