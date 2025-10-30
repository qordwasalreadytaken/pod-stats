"""
Page Generator Module
Handles the generation of HTML pages using templates
"""

import os
import json
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape


class PageGenerator:
    def __init__(self, template_dir=None):
        """Initialize the page generator with template directory"""
        if template_dir is None:
            # Default to templates directory relative to project root
            project_root = Path(__file__).parent.parent.parent
            template_dir = project_root / "templates"
        
        self.template_dir = Path(template_dir)
        
        # Set up Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml'])
        )
        
        # Add custom filters
        self.env.filters['tojson'] = self._tojson_filter
    
    def _tojson_filter(self, value):
        """Custom JSON filter for Jinja2"""
        return json.dumps(value)
    
    def generate_special_analysis_page(self, template_data, output_path):
        """Generate a special analysis page using the template"""
        try:
            # Load the special analysis template
            template = self.env.get_template('special_analysis.html')
            
            # Add generation timestamp
            template_data['generation_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Render the template
            html_content = template.render(template_data)
            
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the HTML file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ Generated special analysis page: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating special analysis page {output_path}: {e}")
            return False
    
    def generate_page_from_template(self, template_name, template_data, output_path):
        """Generate any page from a template"""
        try:
            # Load the specified template
            template = self.env.get_template(template_name)
            
            # Add generation timestamp if not already present
            if 'generation_date' not in template_data:
                template_data['generation_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Render the template
            html_content = template.render(template_data)
            
            # Ensure output directory exists
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the HTML file
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"✅ Generated page: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Error generating page {output_path} from template {template_name}: {e}")
            return False
    
    def validate_template(self, template_name):
        """Validate that a template exists and is syntactically correct"""
        try:
            template = self.env.get_template(template_name)
            print(f"✅ Template {template_name} is valid")
            return True
        except Exception as e:
            print(f"❌ Template {template_name} validation failed: {e}")
            return False
    
    def list_available_templates(self):
        """List all available templates in the template directory"""
        if not self.template_dir.exists():
            print(f"❌ Template directory {self.template_dir} does not exist")
            return []
        
        templates = []
        for template_file in self.template_dir.glob('*.html'):
            templates.append(template_file.name)
        
        print(f"📋 Available templates: {', '.join(templates)}")
        return templates
    
    def render_template_string(self, template_string, template_data):
        """Render a template from a string rather than file"""
        try:
            template = self.env.from_string(template_string)
            
            # Add generation timestamp if not already present
            if 'generation_date' not in template_data:
                template_data['generation_date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            return template.render(template_data)
            
        except Exception as e:
            print(f"❌ Error rendering template string: {e}")
            return None


class TemplateManager:
    """Manages template loading and caching"""
    
    def __init__(self, template_dir=None):
        self.page_generator = PageGenerator(template_dir)
        self._template_cache = {}
    
    def get_template_content(self, template_name):
        """Get the raw content of a template file"""
        if template_name in self._template_cache:
            return self._template_cache[template_name]
        
        template_path = self.page_generator.template_dir / template_name
        
        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                content = f.read()
                self._template_cache[template_name] = content
                return content
        except FileNotFoundError:
            print(f"❌ Template {template_name} not found at {template_path}")
            return None
        except Exception as e:
            print(f"❌ Error reading template {template_name}: {e}")
            return None
    
    def update_template(self, template_name, new_content):
        """Update a template file with new content"""
        template_path = self.page_generator.template_dir / template_name
        
        try:
            # Create backup
            backup_path = template_path.with_suffix(f'{template_path.suffix}.backup')
            if template_path.exists():
                import shutil
                shutil.copy2(template_path, backup_path)
                print(f"📋 Created backup: {backup_path}")
            
            # Write new content
            with open(template_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            
            # Clear cache
            if template_name in self._template_cache:
                del self._template_cache[template_name]
            
            print(f"✅ Updated template: {template_name}")
            return True
            
        except Exception as e:
            print(f"❌ Error updating template {template_name}: {e}")
            return False
    
    def create_template_from_example(self, template_name, example_data=None):
        """Create a new template file from example data"""
        if example_data is None:
            example_data = {
                'title': 'Example Page',
                'content': 'This is example content',
                'generation_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
        
        basic_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }} - Path of Diablo Analytics</title>
    <link rel="stylesheet" href="../assets/css/bootstrap.min.css">
    <link rel="stylesheet" href="../assets/css/style.css">
</head>
<body>
    <div class="container my-5">
        <h1>{{ title }}</h1>
        <div class="content">
            {{ content|safe }}
        </div>
        <footer class="mt-5">
            <p class="text-muted">Generated on {{ generation_date }}</p>
        </footer>
    </div>
    <script src="../assets/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
        
        return self.update_template(template_name, basic_template)
    
    def validate_all_templates(self):
        """Validate all templates in the template directory"""
        templates = self.page_generator.list_available_templates()
        results = {}
        
        for template in templates:
            results[template] = self.page_generator.validate_template(template)
        
        return results