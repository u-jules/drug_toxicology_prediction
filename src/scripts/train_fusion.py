import os
import sys

sys.path.append('../')
sys.path.append(os.getcwd())

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import time

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, RGCNConv, global_mean_pool
from torch_geometric.data import Data
from torch_geometric.loader import DataLoader

from rdkit import Chem
from rdkit.Chem import AllChem

from src.utils.constants import HOME_DIR, DATA_DIR, EMBED_DIR, CHKPT_DIR, LOSS_DIR
from src.utils.data_prep import load_embeddings
from src.model.fusion import FusionMLP


def main():
    # Load embeddings
    data = load_embeddings('GNN_embeddings_20241210-043903', 'LLM_embeddings_20241210-035121')

    train_x, train_y = data['train_x'], data['train_y']
    val_x, val_y = data['val_x'], data['val_y']
    test_x, test_y = data['test_x'], data['test_y']

    # Dataloaders
    train_loader = DataLoader(list(zip(train_x, train_y)), batch_size=64, shuffle=True)
    val_loader = DataLoader(list(zip(val_x, val_y)), batch_size=64, shuffle=False)
    test_loader = DataLoader(list(zip(test_x, test_y)), batch_size=64, shuffle=False)

    # Train MLP
    model = FusionMLP(input_dim=train_x.shape[1])
    optimizer = torch.optim.Adam(model.parameters(), lr=1e-3, weight_decay=1e-3)
    criterion = nn.MSELoss()

    train_losses = []
    val_losses = []

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)

    # Training loop with eval on validation set
    # Store model with best validation loss
    min_val_loss = np.inf
    min_val_model = None
    min_val_epoch = None
    for epoch in range(100):
        model.train()
        total_train_loss = 0

        for batch in train_loader:
            x, y = batch

            optimizer.zero_grad()
            y_pred = model(x).squeeze()
            loss = criterion(y_pred, y)
            loss.backward()
            optimizer.step()

            total_train_loss += loss.item()
        total_train_loss /= len(train_loader)
        train_losses.append(total_train_loss)

        # Validation
        model.eval()
        total_val_loss = 0
        with torch.no_grad():
            for batch in val_loader:
                x, y = batch

                y_pred = model(x).squeeze()
                loss = criterion(y_pred, y)
                total_val_loss += loss.item()
        total_val_loss /= len(val_loader)

        if total_val_loss < min_val_loss:
            min_val_loss = total_val_loss
            min_val_model = model.state_dict()
            min_val_epoch = epoch

        val_losses.append(total_val_loss)

        print(f'Epoch {epoch+1}, Train Loss: {train_losses[-1]:.4f}, Val Loss: {val_losses[-1]:.4f}')

    # Save best model
    cur_time = time.strftime('%Y%m%d-%H%M%S')
    torch.save(min_val_model, os.path.join(CHKPT_DIR, f'fusion_{cur_time}_epoch_{min_val_epoch}.pth'))

    # Save losses
    losses = pd.DataFrame({'train_loss': train_losses, 'val_loss': val_losses})
    losses.to_csv(os.path.join(LOSS_DIR, f'fusion_{cur_time}_epoch_{min_val_epoch}.csv'), index=False)


if __name__ == '__main__':
    main()