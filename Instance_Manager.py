import threading

class InstanceManager:
    def __init__(self):
        self._instances = {}
        self._factories = {}
        self._lock = threading.Lock()

    def set_instance(self, key, instance_or_factory):
        """Saves an instance for the specified key."""
        with self._lock:
            if key in self._instances or key in self._factories:
                raise ValueError(f"An instance with the key '{key}' already exists!")
            else: 
                if callable(instance_or_factory):
                    self._factories[key] = instance_or_factory
                else:
                    self._instances[key] = instance_or_factory

    def get_instance(self, key):
        """Returns the instance for the specified key. If it doesn't exist, it tries to create it using the factory."""
        with self._lock:
            if key in self._instances:
                return self._instances[key]
            elif key in self._factories:
                self._instances[key] = self._factories[key]()  # Create and save instance
                return self._instances[key]
            else:
                raise ValueError(f"Instance '{key}' not found!")
    
    def print_instances(self):
        """Outputs all stored instances."""
        print(f"Currently stored instances: {self._instances}\n and Factories: {self._factories}")

    def reset_instance(self, key):
        """Removes the instance for the specified key."""
        with self._lock:
            if key in self._instances:
                del self._instances[key]
            else:
                raise KeyError(f"No instance with the key ‘{key}’ found!")
            
IM = InstanceManager()
