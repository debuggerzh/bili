# -*- coding:utf-8 -*-
# bert文本分类baseline模型
# model: bert
# 本文件在项目根目录下执行
import csv
import os
import pandas as pd
from pandas import DataFrame
from urllib3 import disable_warnings
import torch
import torch.nn as nn
import torch.utils.data as Data
import torch.optim as optim
from transformers import AutoModel, AutoTokenizer

os.environ['CURL_CA_BUNDLE'] = ''
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "max_split_size_mb:32"
disable_warnings()  # 忽略！InsecureRequestWarning
train_curve = []
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

batch_size = 64
epoches = 50
model = "bert-base-chinese"
hidden_size = 768
n_class = 2
maxlen = 8

# data
test_csv = pd.read_csv(os.path.join('resources', 'gender_text.csv'))
sentences = test_csv['text'].tolist()
labels = test_csv['gender'].tolist()


# sentences = ["我喜欢打篮球", "这个相机很好看", "今天玩的特别开心", "我不喜欢你", "太糟糕了", "真是件令人伤心的事情"]
# labels = [1, 1, 1, 0, 0, 0]  # 1积极, 0消极.


class MyDataset(Data.Dataset):
    def __init__(self, sentences, labels=None, with_labels=True, ):
        self.tokenizer = AutoTokenizer.from_pretrained(model)
        self.with_labels = with_labels
        self.sentences = sentences
        self.labels = labels

    def __len__(self):
        return len(sentences)

    def __getitem__(self, index):
        # Selecting sentence1 and sentence2 at the specified index in the data frame
        sent = self.sentences[index]

        # Tokenize the pair of sentences to get token ids, attention masks and token type ids
        encoded_pair = self.tokenizer(sent,
                                      padding='max_length',  # Pad to max_length
                                      truncation=True,  # Truncate to max_length
                                      max_length=maxlen,
                                      return_tensors='pt')  # Return torch.Tensor objects

        token_ids = encoded_pair['input_ids'].squeeze(0)  # tensor of token ids
        attn_masks = encoded_pair['attention_mask'].squeeze(
            0)  # binary tensor with "0" for padded values and "1" for the other values
        token_type_ids = encoded_pair['token_type_ids'].squeeze(
            0)  # binary tensor with "0" for the 1st sentence tokens & "1" for the 2nd sentence tokens

        if self.with_labels:  # True if the dataset has labels
            label = self.labels[index]
            return token_ids, attn_masks, token_type_ids, label
        else:
            return token_ids, attn_masks, token_type_ids


# model
class BertClassify(nn.Module):
    def __init__(self):
        super(BertClassify, self).__init__()
        self.bert = AutoModel.from_pretrained(model, output_hidden_states=True, return_dict=True)
        self.linear = nn.Linear(hidden_size, n_class)
        self.dropout = nn.Dropout(0.5)

    def forward(self, x):
        input_ids, attention_mask, token_type_ids = x[0], x[1], x[2]
        outputs = self.bert(input_ids=input_ids, attention_mask=attention_mask,
                            token_type_ids=token_type_ids)  # 返回一个output字典
        # 用最后一层cls向量做分类
        # outputs.pooler_output: [bs, hidden_size]
        logits = self.linear(self.dropout(outputs.pooler_output))
        return logits


train = Data.DataLoader(dataset=MyDataset(sentences, labels), batch_size=batch_size, shuffle=True, num_workers=1)
bc = BertClassify().to(device)
optimizer = optim.Adam(bc.parameters(), lr=1e-3, weight_decay=1e-2)
loss_fn = nn.CrossEntropyLoss()


def classify_test(df: DataFrame):
    classify_train()

    bc.eval()
    with torch.no_grad():
        # df = pd.read_csv(file)
        test_text = df['text'].tolist()
        test = MyDataset(test_text, labels=None, with_labels=False)
        # fname 已经包含后缀
        # predict_file = os.path.join('predict', os.path.basename(file))
        # with open(predict_file, mode='w', encoding='utf-8', newline='') as predict:
        #     writer = csv.writer(predict)
        #     writer.writerow(('text', 'predicted_gender'))
        gender_list = []
        for idx in range(len(test)):
            try:
                x = test.__getitem__(idx)
            except:
                continue
            x = tuple(p.unsqueeze(0).to(device) for p in x)
            test_pred = bc([x[0], x[1], x[2]])
            test_pred = test_pred.data.max(dim=1, keepdim=True)[1]
            if test_pred[0][0] == 0:
                gender = 0  # 女
                gender_list.append(0)
            else:
                gender = 1  # 男
                gender_list.append(1)
            print(test_text[idx], gender)
            # writer.writerow((test_text[idx], gender))
        df['p_gender'] = gender_list
        return df


def classify_train():
    total_step = len(train)
    for epoch in range(epoches):
        sum_loss = 0
        for i, batch in enumerate(train):
            optimizer.zero_grad()
            batch = tuple(p.to(device) for p in batch)
            pred = bc([batch[0], batch[1], batch[2]])
            loss = loss_fn(pred, batch[3])
            sum_loss += loss.item()

            loss.backward()
            optimizer.step()
            print('[{}|{}] step:{}/{} loss:{:.4f}'.format(epoch + 1, epoches, i + 1, total_step, loss.item()))
        train_curve.append(sum_loss)


if __name__ == '__main__':
    # train
    classify_test(r'../resources/danmakus/1095720802.csv')
