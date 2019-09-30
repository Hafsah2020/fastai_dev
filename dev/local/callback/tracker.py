#AUTOGENERATED! DO NOT EDIT! File to edit: dev/17_callback_tracker.ipynb (unless otherwise specified).

__all__ = ['TerminateOnNaNCallback', 'TrackerCallback', 'EarlyStoppingCallback', 'SaveModelCallback',
           'ReduceLROnPlateau']

#Cell
from ..torch_basics import *
from ..test import *
from ..layers import *
from ..data.all import *
from ..notebook.showdoc import show_doc
from ..optimizer import *
from ..learner import *
from .progress import *

#Cell
class TerminateOnNaNCallback(Callback):
    "A `Callback` that terminates training if loss is NaN."
    run_before=Recorder

    def after_batch(self):
        "Test if `last_loss` is NaN and interrupts training."
        if torch.isinf(self.loss) or torch.isnan(self.loss): raise CancelFitException

#Cell
class TrackerCallback(Callback):
    "A `Callback` that keeps track of the best value in `monitor`."
    run_after=Recorder

    def __init__(self, monitor='valid_loss', comp=None, min_delta=0.):
        if comp is None: comp = np.less if 'loss' in monitor else np.greater
        if comp == np.less: min_delta *= -1
        self.monitor,self.comp,self.min_delta = monitor,comp,min_delta

    def begin_fit(self):
        "Prepare the monitored value"
        self.best = float('inf') if self.comp == np.less else -float('inf')
        assert self.monitor in self.recorder.metric_names[1:]
        self.idx = self.recorder.metric_names[1:].index(self.monitor)

    def after_epoch(self):
        "Compare the last value to the best up to know"
        val = self.recorder.values[-1][self.idx]
        if self.comp(val - self.min_delta, self.best): self.best,self.new_best = val,True
        else: self.new_best = False

#Cell
class EarlyStoppingCallback(TrackerCallback):
    "A `TrackerCallback` that terminates training when monitored quantity stops improving."
    def __init__(self, monitor='valid_loss', comp=None, min_delta=0., patience=1):
        super().__init__(monitor=monitor, comp=comp, min_delta=min_delta)
        self.patience = patience

    def begin_fit(self): self.wait = 0; super().begin_fit()
    def after_epoch(self):
        "Compare the value monitored to its best score and maybe stop training."
        super().after_epoch()
        if self.new_best: self.wait = 0
        else:
            self.wait += 1
            if self.wait >= self.patience:
                print(f'No improvement since epoch {self.epoch-self.wait}: early stopping')
                raise CancelFitException()

#Cell
class SaveModelCallback(TrackerCallback):
    "A `TrackerCallback` that terminates training when monitored quantity stops improving."
    def __init__(self, monitor='valid_loss', comp=None, min_delta=0., fname='model', every_epoch=False):
        super().__init__(monitor=monitor, comp=comp, min_delta=min_delta)
        store_attr(self, 'fname,every_epoch')

    def after_epoch(self):
        "Compare the value monitored to its best score and maybe stop training."
        if self.every_epoch: self.learn.save(f'{self.fname}_{self.epoch}')
        else: #every improvement
            super().after_epoch()
            if self.new_best: self.learn.save(f'{self.fname}')

    def on_train_end(self, **kwargs):
        "Load the best model."
        if not self.every_epoch and (self.learn.path/f'{self.learn.model_dir}/{self.fname}.pth').is_file():
            self.learn.load(f'{self.fname}')

#Cell
class ReduceLROnPlateau(TrackerCallback):
    "A `TrackerCallback` that reduces learning rate when a metric has stopped improving."
    def __init__(self, monitor='valid_loss', comp=None, min_delta=0., patience=1, factor=10.):
        super().__init__(monitor=monitor, comp=comp, min_delta=min_delta)
        self.patience,self.factor = patience,factor

    def begin_fit(self): self.wait = 0; super().begin_fit()
    def after_epoch(self):
        "Compare the value monitored to its best score and maybe stop training."
        super().after_epoch()
        if self.new_best: self.wait = 0
        else:
            self.wait += 1
            if self.wait >= self.patience:
                for h in self.opt.hypers: h['lr'] /= self.factor
                self.wait = 0
                print(f'Epoch {self.epoch}: reducing lr to {self.opt.hypers[-1]["lr"]}')