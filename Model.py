###########
import Utils                
import Config
#############
import time 
import copy
import pandas as pd                                                            
###################
from matplotlib import pyplot as plt
####################################  
import torch                                
import torchvision                          
from torch import nn                        
from torch import optim                        
from torchvision import models            
from torchsummary import summary
from torchvision import datasets            
from torchvision import transforms                      
from torch.optim import lr_scheduler              
from torch.optim.lr_scheduler import ExponentialLR      
##################################################

def load_data(path, batch_size, shuffle):

	data_transforms = transforms.Compose(transforms = [transforms.ToTensor()]) #Create a function get_data_transforms

	images_dataset = datasets.ImageFolder(root = str(path), transform = data_transforms) 
	dataloaders = torch.utils.data.DataLoader(dataset = images_dataset, batch_size = batch_size, shuffle = shuffle, num_workers = 8)

	return dataloaders, images_dataset

def create_model(device = Config.device):
                                                
    model = models.resnet18(pretrained = True)  
    num_ftrs = model.fc.in_features             
    model.fc = nn.Linear(num_ftrs, 6)              
    model_summary = summary(model, (3,224,224))
    model.to(device)

    return model

def get_current_lr(opt):

	current_lr = None
	for group in opt.param_groups:
		current_lr = group["lr"]

	return current_lr

def metrics_batch(output, target):
	
	predicted = torch.argmax(output, dim = 1, keepdim = True)
	corrects = predicted.eq(target.view_as(predicted)).sum().item()

	return corrects    

def train_val(num_epochs = Config.args.num_epochs, batch_size = Config.args.batch_size, 
	weight_decay = Config.args.weight_decay, path2weights = Config.args.Path2Weights, 
	learning_rate = Config.args.learning_rate, learning_rate_decay = Config.args.learning_rate_decay, 
	Train_Patches_path = Config.args.Train_Patches, Validation_Patches_path = Config.args.Validation_Patches, 
	sanity_check = Config.args.Sanity_Check, loss_function = nn.CrossEntropyLoss()):

	since = time.time()

	train_loader, train_set = load_data(path = Train_Patches_path, batch_size = batch_size, shuffle = True)
	val_loader, val_set = load_data(path = Validation_Patches_path, batch_size = batch_size, shuffle = False)

	model = create_model()
	best_model = copy.deepcopy(model.state_dict())
	best_loss = float("inf")

	opt = optim.Adam(params = model.parameters(), lr = learning_rate, weight_decay = weight_decay)
	scheduler = lr_scheduler.ExponentialLR(optimizer = opt, gamma = learning_rate_decay)

	#Initialize from best_model and checkpoint
	#Print the model's hyperparameters #Code a seprate function to print

	loss_history = {"train": [], "val": []}
	metric_history = {"train": [], "val": []}

	for epoch in range(num_epochs):

		current_lr = get_current_lr(opt)
		print('Epoch {}/{}, current lr={}'.format(epoch + 1, num_epochs, current_lr))

		model.train()
		train_running_loss = 0.0
		train_runing_metric = 0.0
		train_running_corrects = 0.0

		for i, (inputs, labels) in enumerate(train_loader):

			train_inputs = inputs.to(device)
			train_labels = labels.to(device)

			train_outputs = model(train_inputs)
			train_metric_b = metrics_batch(train_outputs, train_labels)
			train_loss_b = loss_function(train_outputs, train_labels) 

			opt.zero_grad()
			train_loss_b.backward()
			opt.step()

			train_running_loss += train_loss_b # in deepslide they multiplied it by train_inputs.size(0)

			if train_metric_b is not None:
				train_runing_metric += train_metric_b
		#Add a confusion matrix here

		train_len_data = len(train_set)
		train_loss = train_running_loss / float(train_len_data)
		train_metric = train_runing_metric / float(train_len_data)
		loss_history["train"].append(train_loss)
		metric_history["train"].append(train_metric)

		model.eval()
		val_running_loss = 0.0
		val_runing_metric = 0.0

		for i, (inputs, labels) in enumerate(val_loader):

			val_inputs = inputs.to(device)
			val_labels = labels.to(device)

			with torch.no_grad():
				val_outputs = model(val_inputs)
				val_loss_b = loss_function(val_outputs, val_labels) 
				val_metric_b = metrics_batch(val_outputs, val_labels)

				if val_loss_b < best_loss:
					best_loss = val_loss_b
					best_model = copy.deepcopy(model.state_dict())
					torch.save(model.state_dict(), path2weights) 
					print("Copied best model weights")

			val_running_loss += val_loss_b # in deepslide they multiplied it by val_inputs.size(0)

			if val_metric_b is not None:
				val_runing_metric += val_metric_b

			if sanity_check is True:
				break

		#Add a confusion matrix here

		val_len_data = len(val_set)
		val_loss = val_running_loss / float(val_len_data)
		val_metric = val_runing_metric / float(val_len_data)
		loss_history["val"].append(val_loss)
		metric_history["val"].append(val_metric)

		scheduler.step()

		print("train loss: %.6f, val loss: %.6f, accuracy: %.2f"%(train_loss, val_loss, 100*val_metric))

		#Create a checkpoint 
	#Create a csv file to store loss_history and metric_history
	
	print(f"\ntraining complete in " f"{(time.time() - since) // 60:.2f} minutes")

	model.load_state_dict(best_model)

	return model, loss_history, metric_history

def predict(model, batch_size = Config.args.batch_size, Test_Patches_path = Config.args.Test_Patches, device = Config.device):
"""
	model.eval()

	classes = Config.args.Classes

	test_loader, test_set = load_data(path = Test_Patches_path, batch_size = batch_size, shuffle = False)
	test_len_data = len(test_set)
	
	output_file = Utils.create_folder(Config.args.Predictions) 
"""
	#https://stackoverflow.com/questions/56699048/how-to-get-the-filename-of-a-sample-from-a-dataloader
	#confidences, test_preds = torch.max(nn.Softmax(dim = 1)(model(test_inputs.to(device))), dim = 1)
	pass
				

def plot_graphs(loss_history, metric_history, num_epochs = Config.args.num_epochs):

	plt.title("Train-Val Loss")
	plt.plot(range(1, num_epochs + 1), loss_history["train"], label = "train")
	plt.plot(range(1, num_epochs + 1), loss_history["val"], label = "val")
	plt.ylabel("Loss")
	plt.xlabel("Training Epochs")
	plt.legend()
	plt.show()

	plt.title("Train-Val Accuracy")
	plt.plot(range(1,num_epochs + 1), metric_history["train"], label = "train")
	plt.plot(range(1,num_epochs + 1), metric_history["val"], label = "val")
	plt.ylabel("Accuracy")
	plt.xlabel("Training Epochs")
	plt.legend()
	plt.show()

if __name__ == '__main__':
    best_model, loss_history, metric_history = train_val()
    plot_graphs(loss_history, metric_history)
    #predict(best_model)