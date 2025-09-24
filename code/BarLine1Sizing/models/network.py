import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, TensorDataset
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import matplotlib.pyplot as plt


# 1. 加载和预处理数据
def load_data(file_path):
    df = pd.read_csv(file_path, header=None)
    # 分离特征和目标列（最后1列是目标值）
    features = df.iloc[:, 1:-1].values  # 忽略第一列索引
    target = df.iloc[:, -1].values.reshape(-1, 1)
    return features, target


# 2. 数据标准化
def scale_data(features, target):
    feature_scaler = StandardScaler()
    target_scaler = StandardScaler()

    scaled_features = feature_scaler.fit_transform(features)
    scaled_target = target_scaler.fit_transform(target)

    return scaled_features, scaled_target, feature_scaler, target_scaler


# 3. 创建时间序列数据集
def create_sequences(features, target, seq_length):
    xs, ys = [], []
    for i in range(len(features) - seq_length):
        x = features[i:i + seq_length]
        y = target[i + seq_length - 1]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)


# 4. 定义GRU模型
class GRUModel(nn.Module):
    def __init__(self, input_size, hidden_size, num_layers, output_size):
        super(GRUModel, self).__init__()
        self.gru = nn.GRU(
            input_size=input_size,
            hidden_size=hidden_size,
            num_layers=num_layers,
            batch_first=True
        )
        self.fc = nn.Linear(hidden_size, output_size)

    def forward(self, x):
        out, _ = self.gru(x)  # out: (batch, seq, hidden)
        out = out[:, -1, :]  # 取序列最后一个输出
        out = self.fc(out)
        return out


# 5. 训练函数
def train_model(model, train_loader, val_loader, criterion, optimizer, epochs):
    train_losses, val_losses = [], []

    for epoch in range(epochs):
        # 训练阶段
        model.train()
        train_loss = 0
        for X_batch, y_batch in train_loader:
            optimizer.zero_grad()
            outputs = model(X_batch)
            loss = criterion(outputs, y_batch)
            loss.backward()
            optimizer.step()
            train_loss += loss.item()

        # 验证阶段
        model.eval()
        val_loss = 0
        with torch.no_grad():
            for X_val, y_val in val_loader:
                outputs = model(X_val)
                loss = criterion(outputs, y_val)
                val_loss += loss.item()

        # 记录损失
        avg_train_loss = train_loss / len(train_loader)
        avg_val_loss = val_loss / len(val_loader)
        train_losses.append(avg_train_loss)
        val_losses.append(avg_val_loss)

        print(f'Epoch [{epoch + 1}/{epochs}], '
              f'Train Loss: {avg_train_loss:.6f}, '
              f'Val Loss: {avg_val_loss:.6f}')

    return train_losses, val_losses


# 主程序
if __name__ == "__main__":
    # 参数设置
    SEQ_LENGTH = 10
    BATCH_SIZE = 16
    HIDDEN_SIZE = 64
    NUM_LAYERS = 2
    EPOCHS = 100
    LR = 0.001

    # 1. 加载数据
    features, target = load_data('output.csv')

    # 2. 数据标准化
    scaled_features, scaled_target, feature_scaler, target_scaler = scale_data(features, target)

    # 3. 创建序列
    X, y = create_sequences(scaled_features, scaled_target, SEQ_LENGTH)

    # 4. 划分数据集
    X_train, X_temp, y_train, y_temp = train_test_split(
        X, y, test_size=0.3, shuffle=False
    )
    X_val, X_test, y_val, y_test = train_test_split(
        X_temp, y_temp, test_size=0.5, shuffle=False
    )

    # 转换为PyTorch张量
    X_train = torch.tensor(X_train, dtype=torch.float32)
    y_train = torch.tensor(y_train, dtype=torch.float32)
    X_val = torch.tensor(X_val, dtype=torch.float32)
    y_val = torch.tensor(y_val, dtype=torch.float32)
    X_test = torch.tensor(X_test, dtype=torch.float32)
    y_test = torch.tensor(y_test, dtype=torch.float32)

    # 创建数据加载器
    train_dataset = TensorDataset(X_train, y_train)
    val_dataset = TensorDataset(X_val, y_val)
    test_dataset = TensorDataset(X_test, y_test)

    train_loader = DataLoader(train_dataset, batch_size=BATCH_SIZE, shuffle=False)
    val_loader = DataLoader(val_dataset, batch_size=BATCH_SIZE, shuffle=False)
    test_loader = DataLoader(test_dataset, batch_size=BATCH_SIZE, shuffle=False)

    # 5. 初始化模型
    input_size = X_train.shape[2]  # 特征数量
    output_size = 1
    model = GRUModel(input_size, HIDDEN_SIZE, NUM_LAYERS, output_size)

    # 损失函数和优化器
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)

    # 6. 训练模型
    train_losses, val_losses = train_model(
        model, train_loader, val_loader, criterion, optimizer, EPOCHS
    )

    # 7. 评估测试集
    model.eval()
    test_loss = 0
    predictions = []
    actuals = []

    with torch.no_grad():
        for X_test_batch, y_test_batch in test_loader:
            outputs = model(X_test_batch)
            loss = criterion(outputs, y_test_batch)
            test_loss += loss.item()

            # 保存预测结果
            predictions.extend(outputs.numpy())
            actuals.extend(y_test_batch.numpy())

    avg_test_loss = test_loss / len(test_loader)
    print(f'Test Loss: {avg_test_loss:.6f}')

    # 8. 反标准化结果
    predictions = np.array(predictions).reshape(-1, 1)
    actuals = np.array(actuals).reshape(-1, 1)

    pred_inverse = target_scaler.inverse_transform(predictions)
    actual_inverse = target_scaler.inverse_transform(actuals)

    # 9. 可视化结果
    plt.figure(figsize=(15, 6))

    plt.subplot(1, 2, 1)
    plt.plot(train_losses, label='Train Loss')
    plt.plot(val_losses, label='Validation Loss')
    plt.title('Training and Validation Loss')
    plt.xlabel('Epochs')
    plt.ylabel('MSE Loss')
    plt.legend()
    plt.grid(True)

    plt.subplot(1, 2, 2)
    plt.plot(actual_inverse, label='Actual Values', alpha=0.7)
    plt.plot(pred_inverse, label='Predicted Values', linestyle='--')
    plt.title('Actual vs Predicted Values')
    plt.xlabel('Time Steps')
    plt.ylabel('Weight Values')
    plt.legend()
    plt.grid(True)

    plt.tight_layout()
    plt.savefig('gru_results.png')

    # 10. 计算性能指标
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

    mae = mean_absolute_error(actual_inverse, pred_inverse)
    rmse = np.sqrt(mean_squared_error(actual_inverse, pred_inverse))
    r2 = r2_score(actual_inverse, pred_inverse)

    print(f'Performance Metrics:')
    print(f'MAE: {mae:.4f}')
    print(f'RMSE: {rmse:.4f}')
    print(f'R²: {r2:.4f}')