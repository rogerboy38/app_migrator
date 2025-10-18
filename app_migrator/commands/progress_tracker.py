"""
Progress Tracker Module - V5.0.0
Extracted from V4 with enhancements

Features:
- Visual progress tracking
- Time-based progress reporting
- Step-by-step progress display
- Real-time feedback
"""

import time
from datetime import datetime


class ProgressTracker:
    """
    Enterprise progress tracking with visual feedback
    Extracted and enhanced from V4
    """
    
    def __init__(self, app_name, total_steps=4, custom_steps=None):
        """
        Initialize progress tracker
        
        Args:
            app_name: Name of the app/operation being tracked
            total_steps: Total number of steps (default: 4)
            custom_steps: Optional list of custom step descriptions
        """
        self.app_name = app_name
        self.total_steps = total_steps
        self.current_step = 0
        
        # Default steps
        if custom_steps:
            self.steps = custom_steps
        else:
            self.steps = [
                "🔍 Validating migration",
                "📥 Downloading app", 
                "⚙️ Installing app",
                "✅ Finalizing"
            ]
        
        self.start_time = time.time()
        self.step_times = []
    
    def update(self, message=None):
        """
        Update progress with optional custom message
        
        Args:
            message: Optional custom progress message
        """
        self.current_step += 1
        elapsed = int(time.time() - self.start_time)
        
        # Record step time
        self.step_times.append({
            'step': self.current_step,
            'elapsed': elapsed,
            'timestamp': datetime.now().isoformat()
        })
        
        if message:
            print(f"\r🔄 [{self.current_step}/{self.total_steps}] {message} ({elapsed}s)", end="", flush=True)
        else:
            if self.current_step <= len(self.steps):
                step_msg = self.steps[self.current_step - 1]
                print(f"\r🔄 [{self.current_step}/{self.total_steps}] {step_msg} ({elapsed}s)", end="", flush=True)
            else:
                print(f"\r🔄 [{self.current_step}/{self.total_steps}] Processing... ({elapsed}s)", end="", flush=True)
    
    def complete(self):
        """Mark progress as completed"""
        elapsed = int(time.time() - self.start_time)
        print(f"\r✅ [{self.total_steps}/{self.total_steps}] {self.app_name} completed! ({elapsed}s)")
        
        # Print step timing summary
        if len(self.step_times) > 1:
            print("\n⏱️  Step Timing:")
            for i, step_time in enumerate(self.step_times):
                if i == 0:
                    duration = step_time['elapsed']
                else:
                    duration = step_time['elapsed'] - self.step_times[i-1]['elapsed']
                
                step_name = self.steps[i] if i < len(self.steps) else f"Step {i+1}"
                print(f"  {step_name}: {duration}s")
    
    def fail(self, error):
        """
        Mark progress as failed
        
        Args:
            error: Error message or description
        """
        elapsed = int(time.time() - self.start_time)
        print(f"\r❌ [{self.current_step}/{self.total_steps}] {self.app_name} failed: {error} ({elapsed}s)")
    
    def get_elapsed_time(self):
        """Get elapsed time in seconds"""
        return int(time.time() - self.start_time)
    
    def get_progress_percentage(self):
        """Get progress as percentage"""
        if self.total_steps == 0:
            return 0
        return (self.current_step / self.total_steps) * 100
    
    def display_progress_bar(self, width=50):
        """
        Display visual progress bar
        
        Args:
            width: Width of the progress bar in characters
        """
        percentage = self.get_progress_percentage()
        filled = int(width * self.current_step / self.total_steps)
        bar = '█' * filled + '░' * (width - filled)
        elapsed = self.get_elapsed_time()
        
        print(f"\r[{bar}] {percentage:.1f}% ({elapsed}s)", end="", flush=True)


class MultiStepProgressTracker:
    """
    Multi-step progress tracker for complex operations
    Supports nested progress tracking
    """
    
    def __init__(self, operation_name, steps):
        """
        Initialize multi-step progress tracker
        
        Args:
            operation_name: Name of the operation
            steps: List of step dictionaries with 'name' and optional 'substeps'
        """
        self.operation_name = operation_name
        self.steps = steps
        self.total_steps = len(steps)
        self.current_step = 0
        self.start_time = time.time()
        self.completed_steps = []
        self.failed_steps = []
    
    def start_step(self, step_index):
        """Start a specific step"""
        if step_index < len(self.steps):
            self.current_step = step_index
            step = self.steps[step_index]
            elapsed = int(time.time() - self.start_time)
            print(f"\n🔄 Step {step_index + 1}/{self.total_steps}: {step['name']} ({elapsed}s)")
    
    def complete_step(self, step_index, message=None):
        """Mark a step as completed"""
        if step_index < len(self.steps):
            step = self.steps[step_index]
            elapsed = int(time.time() - self.start_time)
            
            self.completed_steps.append({
                'index': step_index,
                'name': step['name'],
                'elapsed': elapsed,
                'message': message
            })
            
            if message:
                print(f"  ✅ {step['name']}: {message}")
            else:
                print(f"  ✅ {step['name']} completed")
    
    def fail_step(self, step_index, error):
        """Mark a step as failed"""
        if step_index < len(self.steps):
            step = self.steps[step_index]
            elapsed = int(time.time() - self.start_time)
            
            self.failed_steps.append({
                'index': step_index,
                'name': step['name'],
                'elapsed': elapsed,
                'error': error
            })
            
            print(f"  ❌ {step['name']}: {error}")
    
    def complete(self):
        """Mark entire operation as completed"""
        elapsed = int(time.time() - self.start_time)
        print(f"\n🎉 {self.operation_name} completed in {elapsed}s!")
        
        # Summary
        print("\n📊 Summary:")
        print(f"  ✅ Completed: {len(self.completed_steps)}/{self.total_steps}")
        if self.failed_steps:
            print(f"  ❌ Failed: {len(self.failed_steps)}")
    
    def display_summary(self):
        """Display detailed summary"""
        print(f"\n📊 {self.operation_name} Summary")
        print("=" * 70)
        
        print("\n✅ Completed Steps:")
        for step in self.completed_steps:
            print(f"  {step['index'] + 1}. {step['name']} ({step['elapsed']}s)")
            if step.get('message'):
                print(f"      {step['message']}")
        
        if self.failed_steps:
            print("\n❌ Failed Steps:")
            for step in self.failed_steps:
                print(f"  {step['index'] + 1}. {step['name']} ({step['elapsed']}s)")
                print(f"      Error: {step['error']}")
        
        print("=" * 70)


def run_with_progress(func, description, *args, **kwargs):
    """
    Run a function with simple progress tracking
    
    Args:
        func: Function to execute
        description: Description of the operation
        *args, **kwargs: Arguments to pass to the function
    
    Returns:
        Result of the function
    """
    tracker = ProgressTracker(description, total_steps=1, custom_steps=[description])
    tracker.update()
    
    try:
        result = func(*args, **kwargs)
        tracker.complete()
        return result
    except Exception as e:
        tracker.fail(str(e))
        raise


if __name__ == "__main__":
    # Test progress tracker
    print("🧪 Testing Progress Tracker\n")
    
    # Simple progress test
    tracker = ProgressTracker("Test App", total_steps=4)
    
    for i in range(4):
        tracker.update()
        time.sleep(1)
    
    tracker.complete()
    
    # Multi-step progress test
    print("\n\n🧪 Testing Multi-Step Progress Tracker\n")
    
    steps = [
        {'name': 'Analyze app'},
        {'name': 'Validate migration'},
        {'name': 'Execute migration'},
        {'name': 'Verify results'}
    ]
    
    multi_tracker = MultiStepProgressTracker("Migration Process", steps)
    
    for i, step in enumerate(steps):
        multi_tracker.start_step(i)
        time.sleep(1)
        if i < 3:
            multi_tracker.complete_step(i, f"{step['name']} successful")
        else:
            multi_tracker.fail_step(i, "Simulated error")
    
    multi_tracker.display_summary()
