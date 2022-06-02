import importlib

import cloudpickle


class DaskPickleByValue:
    def __getstate__(self) -> dict:
        """
        Make this object unpickleable to dask without its package being installed on workers, via a horrible hack.
        """
        # HACK, awful horrible hack.
        # The implementation of `distributed.protocol.pickle.dumps` currently tries to plain `pickle.dumps`
        # the object. If that raises an error, then it tries `cloudpickle.dumps`.
        # We game this code structure by raising an error every other time we're pickled, forcing the
        # `cloudpickle.dumps` codepath and then succeeding on that one.
        if getattr(self, "_the_first_pickle_is_the_deepest", True):
            self._the_first_pickle_is_the_deepest = False
            raise RuntimeError("cloudpickle time!")
        else:
            del self._the_first_pickle_is_the_deepest

            # Very awkward, but the only way to tell cloudpickle to pickle something by value
            # is by passing it the module whose members you want pickled by value.
            module = importlib.import_module(self.__module__)
            cloudpickle.register_pickle_by_value(module)

            return self.__dict__
