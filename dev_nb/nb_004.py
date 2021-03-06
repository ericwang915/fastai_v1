
        #################################################
        ### THIS FILE WAS AUTOGENERATED! DO NOT EDIT! ###
        #################################################

from nb_002b import *

class Callback():
    def on_train_begin(self): pass         
        #To initiliaze constants in the callback.
    def on_epoch_begin(self): pass
        #At the beginning of each epoch
    def on_batch_begin(self, xb, yb): pass 
        #To set HP before the step is done. A look at the input can be useful (set the lr depending on the seq_len in RNNs, 
        #or for reg_functions called in on_backward_begin)
        #Returns xb, yb (which can allow us to modify the input at that step if needed)
    def on_loss_begin(self, out): pass
        #Called after the forward pass but before the loss has been computed.
        #Passes the output of the model.
        #Returns the output (which can allow us to modify it)
    def on_backward_begin(self, loss): pass
        #Called after the forward pass and the loss has been computed, but before the back propagation.
        #Passes the loss of the model.
        #Returns the loss (which can allow us to modify it, for instance for reg functions)
    def on_backward_end(self): pass
        #Called after the back propagation had been done (and the gradients computed) but before the step of the optimizer.
        #Useful for true weight decay in AdamW
    def on_step_end(self): pass
        #Called after the step of the optimizer but before the gradients are zeroed (not sure this one is useful)
    def on_batch_end(self, loss): pass
        #Called at the end of the batch
    def on_epoch_end(self, val_metrics): pass
        #Called at the end of an epoch
    def on_train_end(self): pass
        #Useful for cleaning up things and saving files/models

class CallbackHandler():
    
    def __init__(self, callbacks):
        self.callbacks = callbacks if callbacks is not None else []
    
    def __call__(self, cb_name, *args, **kwargs):
        return [getattr(cb, f'on_{cb_name}')(*args, **kwargs) for cb in self.callbacks]
    
    def on_train_begin(self): self('train_begin')
    def on_epoch_begin(self): self('epoch_begin')
        
    def on_batch_begin(self, xb, yb):
        for cb in self.callbacks:
            a = cb.on_batch_begin(xb,yb)
            if a is not None: xb,yb = a
        return xb,yb
    
    def on_loss_begin(self, out):
        for cb in self.callbacks:
            a = cb.on_loss_begin(out)
            if a is not None: out = a
        return out
    
    def on_backward_begin(self, loss):
        for cb in self.callbacks:
            a = cb.on_backward_begin(loss)
            if a is not None: loss = a
        return loss
    
    def on_backward_end(self):        self('backward_end')
    def on_step_end(self):            self('step_end')
    def on_batch_end(self, loss):     return np.any(self('batch_end', loss))
    def on_epoch_end(self, val_metrics): return np.any(self('epoch_end', val_metrics))
    def on_train_end(self):           self('train_end')

class HPOptimizer():
    
    def __init__(self, params, opt_fn, init_lr):
        self.opt = opt_fn(params, init_lr)
        self._lr = init_lr
        self.opt_keys = list(self.opt.param_groups[0].keys())
        self.opt_keys.remove('params')
        self.read_defaults()
    
    #Pytorch optimizer methods
    def step(self):
        self.opt.step()
    
    def zero_grad(self):
        self.opt.zero_grad()
    
    #Hyperparameters as properties
    @property
    def lr(self): return self._lr

    @lr.setter
    def lr(self, val):
        self.set_val('lr', val)
        self._lr = val
    
    @property
    def mom(self): return self._mom

    @mom.setter
    def mom(self, val):
        if 'momentum' in self.opt_keys: self.set_val('momentum', val)
        elif 'betas' in self.opt_keys:  self.set_val('betas', (val, self._beta))
        self._mom = val
    
    @property
    def beta(self): return self._beta

    @beta.setter
    def beta(self, val):
        if 'betas' in self.opt_keys:    self.set_val('betas', (self._mom,val))
        elif 'alpha' in self.opt_keys:  self.set_val('alpha', val)
        self._beta = val
    
    @property
    def wd(self): return self._wd

    @wd.setter
    def wd(self, val):
        self.set_val('weight_decay', val)
        self._wd = val
    
    #Helper functions
    def read_defaults(self):
        if 'momentum' in self.opt_keys: self._mom = self.opt.param_groups[0]['momentum']
        if 'alpha' in self.opt_keys: self._beta = self.opt.param_groups[0]['alpha']
        if 'betas' in self.opt_keys: self._mom,self._beta = self.opt.param_groups[0]['betas']
        if 'weight_decay' in self.opt_keys: self._wd = self.opt.param_groups[0]['weight_decay']
    
    def set_val(self, key, val):
        for pg in self.opt.param_groups: pg[key] = val

def annealing_no(start, end, pct): return start
def annealing_linear(start, end, pct): return start + pct * (end-start)
def annealing_exponential(start, end, pct): return start * (end/start) ** pct

def is_tuple(x): return isinstance(x, tuple)

class Stepper():
    
    def __init__(self, vals, num_it, ft=None):
        if is_tuple(vals): self.start,self.end = vals
        else:              self.start,self.end = vals, 0
        #Why does this one doesn't work?
        #(self.start,self.end) = (vals[0],vals[1]) if is_tuple(vals) else vals,0
        self.num_it = num_it
        if ft is None: self.ft = annealing_linear if is_tuple(vals) else annealing_no
        else:          self.ft = ft
        self.n = 0
    
    def step(self):
        self.n += 1
        return self.ft(self.start, self.end, self.n/self.num_it)
    
    def is_done(self):  return self.n >= self.num_it
    def init_val(self): return self.start

class OneCycleScheduler(Callback):
    
    def __init__(self, learn, lr_max, epochs, moms=(0.95,0.85), div_factor=10, pct_end=0.1):
        self.learn = learn
        a = int(len(learn.data.train_dl) * epochs * (1 - pct_end) / 2)
        b = int(len(learn.data.train_dl) * epochs * pct_end)
        self.lr_scheds = [Stepper((lr_max/div_factor, lr_max), a),
                          Stepper((lr_max, lr_max/div_factor), a),
                          Stepper((lr_max/div_factor, lr_max/(div_factor*100)), b)]
        self.mom_scheds = [Stepper(moms, a), Stepper((moms[1], moms[0]), a), Stepper(moms[0], b)]
    
    def on_train_begin(self):
        self.opt = self.learn.opt
        self.opt.lr, self.opt.mom = self.lr_scheds[0].init_val(), self.mom_scheds[0].init_val()
        self.idx_s = 0
    
    def on_batch_end(self, loss):
        self.opt.lr = self.lr_scheds[self.idx_s].step()
        self.opt.mom = self.mom_scheds[self.idx_s].step()
        if self.lr_scheds[self.idx_s].is_done():
            self.idx_s += 1
            if self.idx_s >= len(self.lr_scheds): return True

class LRFinder(Callback):
    #TODO: add model.save in init or on_train_begin and model.load in on_train_end.
    
    def __init__(self, learn, start_lr=1e-5, end_lr=10, num_it=200):
        self.learn = learn
        self.sched = Stepper((start_lr, end_lr), num_it, annealing_exponential)
        #To avoid validating if the train_dl has less than num_it batches, we put aside the valid_dl and remove it
        #during the call to fit.
        self.valid_dl = learn.data.valid_dl
        learn.data.valid_dl = None
    
    def on_train_begin(self):
        self.opt = self.learn.opt
        self.opt.lr = self.sched.init_val()
        self.stop,self.first,self.best_loss = False,True,0.
    
    def on_batch_end(self, loss):
        if self.first or loss < self.best_loss:
            self.first = False
            self.best_loss = loss
        self.opt.lr = self.sched.step()
        if self.sched.is_done() or self.learn.recorder.smooth_loss > 4*self.best_loss:
            #We use the smoothed loss to decide on the stopping since it's less shaky.
            self.stop=True
            return True
    
    def on_epoch_end(self, val_loss): return self.stop
    
    def on_train_end(self):
        #Clean up and put back the valid_dl in its place.
        self.learn.data.valid_dl = self.valid_dl

from typing import Callable, List

@dataclass
class Learner():
    
    data: DataBunch
    model: nn.Module
    loss_fn: Callable = F.cross_entropy
    opt_fn: Callable = optim.SGD
    metrics: List = None
    def __post_init__(self): self.model = self.model.to(data.device)

    def fit(self, epochs, lr, callbacks=None):
        self.opt = HPOptimizer(self.model.parameters(), self.opt_fn, init_lr=lr)
        self.recorder = Recorder(self.opt, self.data.train_dl)
        if callbacks is None: callbacks = []
        callbacks.insert(0, self.recorder)
        fit(epochs, self.model, self.loss_fn, self.opt, self.data, callbacks=callbacks, metrics=self.metrics)
        
    def lr_find(self, start_lr=1e-5, end_lr=10, num_it=200):
        cb = LRFinder(self, start_lr, end_lr, num_it)
        a = int(np.ceil(num_it/len(self.data.train_dl)))
        self.fit(a, start_lr, callbacks=[cb])

def loss_batch(model, xb, yb, loss_fn, opt=None, cb_handler=None, metrics=None):
    out = model(xb)
    if cb_handler is not None: out = cb_handler.on_loss_begin(out)
    loss = loss_fn(out, yb)
    mets = [f(out,yb).item() for f in metrics] if metrics is not None else []
    
    if opt is not None:
        if cb_handler is not None: loss = cb_handler.on_backward_begin(loss)
        loss.backward()
        if cb_handler is not None: cb_handler.on_backward_end()
        opt.step()
        if cb_handler is not None: cb_handler.on_step_end()
        opt.zero_grad()
        
    return (loss.item(),) + tuple(mets) + (len(xb),)

def fit(epochs, model, loss_fn, opt, data, callbacks=None, metrics=None):
    
    cb_handler = CallbackHandler(callbacks)
    cb_handler.on_train_begin()
    
    for epoch in tnrange(epochs):
        model.train()
        cb_handler.on_epoch_begin()
        
        for xb,yb in data.train_dl:
            xb, yb = cb_handler.on_batch_begin(xb, yb)
            loss,_ = loss_batch(model, xb, yb, loss_fn, opt, cb_handler)
            if cb_handler.on_batch_end(loss): break
        
        if hasattr(data,'valid_dl') and data.valid_dl is not None:
            model.eval()
            with torch.no_grad():
                *val_metrics,nums = zip(*[loss_batch(model, xb, yb, loss_fn, metrics=metrics)
                                for xb,yb in data.valid_dl])
            val_metrics = [np.sum(np.multiply(val,nums)) / np.sum(nums) for val in val_metrics]
            
        else: val_metrics=None
        if cb_handler.on_epoch_end(val_metrics): break
        
    cb_handler.on_train_end()

class SmoothenValue():
    
    def __init__(self, beta):
        self.beta,self.n,self.mov_avg = beta,0,0
    
    def add_value(self, val):
        self.n += 1
        self.mov_avg = self.beta * self.mov_avg + (1 - self.beta) * val
        self.smooth = self.mov_avg / (1 - self.beta ** self.n)

class Recorder(Callback):
    beta = 0.98
    
    def __init__(self, opt, train_dl=None):
        self.opt,self.train_dl = opt,train_dl
    
    def on_train_begin(self):
        self.epoch,self.n,self.avg_loss = 0,0,0.
        self.losses,self.val_losses,self.lrs,self.moms,self.metrics = [],[],[],[],[]
        self.smoothener = SmoothenValue(self.beta)
    
    def on_batch_begin(self, xb, yb):
        self.lrs.append(self.opt.lr)
        self.moms.append(self.opt.mom)
        return xb, yb
    
    def on_backward_begin(self, loss):
        #We record the loss here before any other callback has a chance to modify it.
        self.n += 1
        self.smoothener.add_value(loss.item())
        self.smooth_loss = self.smoothener.smooth
        self.losses.append(self.smooth_loss)
        if self.train_dl is not None and self.train_dl.progress_func is not None: 
            self.train_dl.gen.set_postfix_str(self.smooth_loss)
    
    def on_epoch_end(self, val_metrics):
        if val_metrics is not None:
            self.val_losses.append(val_metrics[0])
            if len(val_metrics) > 1: self.metrics.append(val_metrics[1:])
            print(self.epoch, *val_metrics)
        self.epoch += 1
    
    def plot_lr(self, show_moms=False):
        iterations = list(range(len(learn.recorder.lrs)))
        if show_moms:
            fig, axs = plt.subplots(1,2, figsize=(12,4))
            axs[0].plot(iterations, self.lrs)
            axs[1].plot(iterations, self.moms)
        else: plt.plot(iterations, self.lrs)
    
    def plot(self, skip_start=10, skip_end=5):
        lrs = self.lrs[skip_start:-skip_end] if skip_end > 0 else self.lrs[skip_start:]
        losses = self.losses[skip_start:-skip_end] if skip_end > 0 else self.losses[skip_start:]
        fig, ax = plt.subplots(1,1)
        ax.plot(lrs, losses)
        ax.set_xscale('log')