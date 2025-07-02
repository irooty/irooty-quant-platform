class ObjectLoader:
    @staticmethod
    def load(module_path: str, name: str):
        """
        动态加载模块中的类或函数
        """
        module = __import__(module_path, fromlist=[name])
        return getattr(module, name)
