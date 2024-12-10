import os
import sys

sys.path.append('../')
sys.path.append(os.getcwd())

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, RGCNConv, global_mean_pool
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

from rdkit import Chem
from rdkit.Chem import AllChem

from src.utils.constants import HOME_DIR, DATA_DIR


class GCNRegressionModel(nn.Module):
    def __init__(self, input_dim):
        super().__init__()
        self.conv1 = GCNConv(input_dim, 128)  # First GCN layer
        self.conv2 = GCNConv(128, 64)         # Second GCN layer
        self.conv3 = GCNConv(64, 64)         # Third GCN layer
        self.conv4 = GCNConv(64, 32)         # Fourth GCN layer
        self.fc = nn.Linear(32, 1)          # Fully connected layer for regression

    def forward(self, data):
        x, edge_index, batch = data.x, data.edge_index, data.batch

        # Apply GCN layers with ReLU activation
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = self.conv3(x, edge_index)
        x = F.relu(x)
        x = self.conv4(x, edge_index)
        x = F.relu(x)

        # Global mean pooling to aggregate node features for each graph
        x = global_mean_pool(x, batch)

        # Fully connected layer for regression output
        out = self.fc(x)
        return out
    

class RGCNRegressionModel(torch.nn.Module):
    def __init__(self, input_dim, num_edge_types):
        super().__init__()
        self.conv1 = RGCNConv(input_dim, 256, num_relations=num_edge_types)
        self.conv2 = RGCNConv(256, 256, num_relations=num_edge_types)
        self.conv3 = RGCNConv(256, 32, num_relations=num_edge_types)
        self.fc = torch.nn.Linear(32, 1)

    def forward(self, data):
        x, edge_index, edge_type, batch = data.x, data.edge_index, data.edge_type, data.batch

        # Apply RGCN layers with ReLU activation
        x = self.conv1(x, edge_index=edge_index, edge_type=edge_type)
        x = F.relu(x)
        
        x = self.conv2(x, edge_index=edge_index, edge_type=edge_type)
        x = F.relu(x)

        x = self.conv3(x, edge_index=edge_index, edge_type=edge_type)
        x = F.relu(x)
        
        # Global mean pooling to aggregate node features for each graph
        x = global_mean_pool(x, batch)

        # Fully connected layer for regression output
        out = self.fc(x)
        
        return out