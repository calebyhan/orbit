# ORBIT — Test Plan: Modeling & Fusion

*Last edited: 2025-11-06*

## Module Under Test

`orbit.model` — Model heads, gated fusion, training pipeline

---

## Test Scope

**In Scope:**
- Price, news, social model heads
- Gated fusion with burst detection
- Walk-forward training
- Model persistence and loading
- Hyperparameter validation

**Out of Scope:**
- Feature computation (covered in features test plan)
- Backtesting (covered in backtest test plan)

---

## Unit Tests: Model Heads

### Test 1.1: Price Head Architecture

**Objective:** Verify price head structure and forward pass

```python
def test_price_head_architecture():
    """Test price head neural network structure."""
    from orbit.model.heads import PriceHead
    import torch
    
    input_dim = 15  # Price features
    head = PriceHead(input_dim=input_dim, hidden_dim=32)
    
    # Check layers
    assert hasattr(head, 'fc1')
    assert hasattr(head, 'fc2')
    assert hasattr(head, 'output')
    
    # Test forward pass
    batch = torch.randn(10, input_dim)
    output = head(batch)
    
    assert output.shape == (10, 1), f"Expected (10,1), got {output.shape}"
    assert not torch.isnan(output).any(), "Output contains NaN"
```

### Test 1.2: News Head with Attention

**Objective:** Test news head with attention mechanism

```python
def test_news_head_attention():
    """Test news head with self-attention."""
    from orbit.model.heads import NewsHead
    import torch
    
    input_dim = 8  # News features
    head = NewsHead(input_dim=input_dim, hidden_dim=32, use_attention=True)
    
    batch = torch.randn(10, input_dim)
    output, attention_weights = head(batch, return_attention=True)
    
    assert output.shape == (10, 1)
    assert attention_weights.shape[0] == 10
    assert torch.allclose(attention_weights.sum(dim=-1), torch.ones(10)), "Attention weights should sum to 1"
```

### Test 1.3: Social Head Forward Pass

**Objective:** Test social head prediction

```python
def test_social_head_forward():
    """Test social head forward pass."""
    from orbit.model.heads import SocialHead
    import torch
    
    input_dim = 12  # Social features
    head = SocialHead(input_dim=input_dim, hidden_dim=32)
    
    batch = torch.randn(5, input_dim)
    output = head(batch)
    
    assert output.shape == (5, 1)
    assert not torch.isnan(output).any()
    
    # Check output range (should be bounded for signals)
    assert (output >= -1).all() and (output <= 1).all(), "Output should be in [-1, 1]"
```

---

## Unit Tests: Gated Fusion

### Test 2.1: Gate Computation

**Objective:** Test gate value computation from z-scores

```python
def test_gate_computation():
    """Test gate computation from burst z-scores."""
    from orbit.model.fusion import compute_gates
    import torch
    
    # Low z-scores: gate should be ~0 (suppress)
    low_z = torch.tensor([[0.5], [0.3], [-0.2]])
    gates_low = compute_gates(low_z, threshold=2.0)
    
    assert (gates_low < 0.2).all(), "Low z-scores should produce low gates"
    
    # High z-scores: gate should be ~1 (amplify)
    high_z = torch.tensor([[3.5], [4.2], [2.8]])
    gates_high = compute_gates(high_z, threshold=2.0)
    
    assert (gates_high > 0.7).all(), "High z-scores should produce high gates"
```

### Test 2.2: Fusion Forward Pass

**Objective:** Test complete fusion model

```python
def test_fusion_forward_pass():
    """Test gated fusion of three heads."""
    from orbit.model.fusion import GatedFusion
    import torch
    
    fusion = GatedFusion(
        price_dim=15,
        news_dim=8,
        social_dim=12,
        hidden_dim=32
    )
    
    # Sample inputs
    price_features = torch.randn(10, 15)
    news_features = torch.randn(10, 8)
    social_features = torch.randn(10, 12)
    news_z = torch.randn(10, 1)
    social_z = torch.randn(10, 1)
    
    output = fusion(price_features, news_features, social_features, news_z, social_z)
    
    assert output.shape == (10, 1)
    assert not torch.isnan(output).any()
```

### Test 2.3: Burst Amplification

**Objective:** Verify burst events amplify signals

```python
def test_burst_amplification():
    """Test that burst events amplify modality signals."""
    from orbit.model.fusion import GatedFusion
    import torch
    
    fusion = GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=32)
    
    # Fixed price/social, vary news burst
    price_features = torch.randn(2, 15)
    news_features = torch.randn(2, 8)
    social_features = torch.randn(2, 12)
    
    # Normal news (z=0.5)
    normal_z = torch.tensor([[0.5], [0.5]])
    social_z = torch.tensor([[0.0], [0.0]])
    
    output_normal = fusion(price_features, news_features, social_features, normal_z, social_z)
    
    # Burst news (z=4.0)
    burst_z = torch.tensor([[4.0], [4.0]])
    output_burst = fusion(price_features, news_features, social_features, burst_z, social_z)
    
    # Burst should produce larger magnitude signal
    assert torch.abs(output_burst).mean() > torch.abs(output_normal).mean(), \
        "Burst should amplify signal"
```

---

## Integration Tests: Training

### Test 3.1: Single Epoch Training

**Objective:** Test one training epoch completes

```python
def test_single_epoch_training():
    """Test training for one epoch."""
    from orbit.model.train import train_model
    import torch
    from torch.utils.data import TensorDataset, DataLoader
    
    # Create synthetic dataset
    X_price = torch.randn(100, 15)
    X_news = torch.randn(100, 8)
    X_social = torch.randn(100, 12)
    news_z = torch.randn(100, 1)
    social_z = torch.randn(100, 1)
    y = torch.randn(100, 1)  # Target returns
    
    dataset = TensorDataset(X_price, X_news, X_social, news_z, social_z, y)
    dataloader = DataLoader(dataset, batch_size=16)
    
    model = GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=32)
    
    loss_before = compute_loss(model, dataloader)
    
    train_model(model, dataloader, epochs=1, lr=0.001)
    
    loss_after = compute_loss(model, dataloader)
    
    assert loss_after < loss_before, "Loss should decrease after training"
```

### Test 3.2: Walk-Forward Training

**Objective:** Test walk-forward cross-validation

```python
def test_walk_forward_training(tmp_path):
    """Test walk-forward training over multiple windows."""
    from orbit.model.train import walk_forward_train
    import pandas as pd
    
    # Generate 60 days of features
    dates = pd.date_range('2024-09-01', periods=60, freq='B')
    features = []
    
    for date in dates:
        df = pd.DataFrame({
            'date': [date],
            'symbol': ['SPY'],
            'log_return': [np.random.randn() * 0.02],
            'target_1d': [np.random.randn() * 0.02]
        })
        features.append(df)
    
    all_features = pd.concat(features)
    
    config = {
        'train_window_days': 20,
        'test_window_days': 5,
        'retrain_freq_days': 5
    }
    
    results = walk_forward_train(all_features, config)
    
    # Should have ~8 training windows (60 days / 5 retrain freq)
    assert len(results['windows']) >= 7
    
    # Each window should have train/val loss
    for window in results['windows']:
        assert 'train_loss' in window
        assert 'val_loss' in window
        assert window['train_loss'] > 0
```

### Test 3.3: Model Persistence

**Objective:** Test saving and loading models

```python
def test_model_persistence(tmp_path):
    """Test saving and loading trained model."""
    from orbit.model.fusion import GatedFusion
    import torch
    
    model = GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=32)
    
    # Set some weights
    with torch.no_grad():
        model.price_head.fc1.weight.fill_(0.5)
    
    # Save
    model_path = tmp_path / 'model.pt'
    torch.save(model.state_dict(), model_path)
    
    # Load into new model
    model_loaded = GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=32)
    model_loaded.load_state_dict(torch.load(model_path))
    
    # Verify weights match
    assert torch.allclose(
        model.price_head.fc1.weight,
        model_loaded.price_head.fc1.weight
    ), "Loaded weights should match saved weights"
```

---

## Data Quality Tests

### Test 4.1: No Gradient Explosion

**Objective:** Ensure gradients stay bounded during training

```python
def test_no_gradient_explosion():
    """Test that gradients don't explode during training."""
    from orbit.model.train import train_model
    import torch
    
    # Create challenging dataset (high variance)
    X_price = torch.randn(100, 15) * 10
    X_news = torch.randn(100, 8) * 10
    X_social = torch.randn(100, 12) * 10
    news_z = torch.randn(100, 1)
    social_z = torch.randn(100, 1)
    y = torch.randn(100, 1) * 10
    
    dataset = TensorDataset(X_price, X_news, X_social, news_z, social_z, y)
    dataloader = DataLoader(dataset, batch_size=16)
    
    model = GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=32)
    
    # Train with gradient tracking
    max_grad = train_model(model, dataloader, epochs=5, lr=0.001, track_gradients=True)
    
    assert max_grad < 100, f"Max gradient {max_grad} indicates instability"
```

### Test 4.2: Target Leakage Check

**Objective:** Ensure no future data in features

```python
def test_target_leakage():
    """Test that features don't contain future information."""
    from orbit.model.data import prepare_training_data
    import pandas as pd
    
    # Features with date 2024-11-05
    df = pd.DataFrame({
        'date': ['2024-11-05'],
        'symbol': ['SPY'],
        'log_return': [0.02],  # Same-day return
        'sentiment_news': [0.5],
        'target_1d': [0.03]  # Next-day return
    })
    
    X, y = prepare_training_data(df)
    
    # X should not contain target
    assert 'target_1d' not in X.columns, "Features should not include target"
    
    # Y should be aligned with next day
    # This test checks temporal alignment in prepare_training_data
```

### Test 4.3: Reproducibility

**Objective:** Test training is reproducible with fixed seed

```python
def test_training_reproducibility():
    """Test that training is reproducible with fixed seed."""
    from orbit.model.train import train_model
    import torch
    import numpy as np
    
    def train_with_seed(seed):
        torch.manual_seed(seed)
        np.random.seed(seed)
        
        X_price = torch.randn(100, 15)
        X_news = torch.randn(100, 8)
        X_social = torch.randn(100, 12)
        news_z = torch.randn(100, 1)
        social_z = torch.randn(100, 1)
        y = torch.randn(100, 1)
        
        dataset = TensorDataset(X_price, X_news, X_social, news_z, social_z, y)
        dataloader = DataLoader(dataset, batch_size=16)
        
        model = GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=32)
        train_model(model, dataloader, epochs=3, lr=0.001)
        
        return model.state_dict()
    
    # Train twice with same seed
    state_dict_1 = train_with_seed(42)
    state_dict_2 = train_with_seed(42)
    
    # Check all parameters match
    for key in state_dict_1.keys():
        assert torch.allclose(state_dict_1[key], state_dict_2[key]), \
            f"Parameter {key} differs between runs"
```

---

## Performance Tests

### Test 5.1: Training Speed

**Objective:** Verify training completes in time budget

```python
def test_training_speed():
    """Test that training completes within 10 minutes."""
    import time
    from orbit.model.train import train_model
    
    # Realistic dataset size
    X_price = torch.randn(1000, 15)
    X_news = torch.randn(1000, 8)
    X_social = torch.randn(1000, 12)
    news_z = torch.randn(1000, 1)
    social_z = torch.randn(1000, 1)
    y = torch.randn(1000, 1)
    
    dataset = TensorDataset(X_price, X_news, X_social, news_z, social_z, y)
    dataloader = DataLoader(dataset, batch_size=32)
    
    model = GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=32)
    
    start = time.time()
    train_model(model, dataloader, epochs=10, lr=0.001)
    duration = time.time() - start
    
    assert duration < 600, f"Training took {duration}s, exceeds 10min limit"
```

### Test 5.2: Inference Speed

**Objective:** Test prediction latency

```python
def test_inference_speed():
    """Test that inference is fast enough for daily scoring."""
    from orbit.model.fusion import GatedFusion
    import torch
    import time
    
    model = GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=32)
    model.eval()
    
    # Batch of 3 symbols (SPY, VOO, ^SPX)
    X_price = torch.randn(3, 15)
    X_news = torch.randn(3, 8)
    X_social = torch.randn(3, 12)
    news_z = torch.randn(3, 1)
    social_z = torch.randn(3, 1)
    
    # Warm-up
    with torch.no_grad():
        model(X_price, X_news, X_social, news_z, social_z)
    
    # Measure 100 inferences
    start = time.time()
    for _ in range(100):
        with torch.no_grad():
            output = model(X_price, X_news, X_social, news_z, social_z)
    duration = time.time() - start
    
    avg_latency = duration / 100
    assert avg_latency < 0.01, f"Avg inference {avg_latency}s, should be <10ms"
```

---

## Hyperparameter Tests

### Test 6.1: Learning Rate Validation

**Objective:** Test hyperparameter validation

```python
def test_learning_rate_validation():
    """Test that invalid learning rates are rejected."""
    from orbit.model.train import validate_hyperparams
    
    # Valid
    valid_hp = {'learning_rate': 0.001, 'batch_size': 32, 'epochs': 10}
    errors = validate_hyperparams(valid_hp)
    assert len(errors) == 0
    
    # Invalid: negative LR
    invalid_hp = {'learning_rate': -0.001, 'batch_size': 32, 'epochs': 10}
    errors = validate_hyperparams(invalid_hp)
    assert 'learning_rate' in str(errors)
    
    # Invalid: too large LR
    invalid_hp = {'learning_rate': 1.0, 'batch_size': 32, 'epochs': 10}
    errors = validate_hyperparams(invalid_hp)
    assert 'learning_rate' in str(errors)
```

### Test 6.2: Hidden Dimension Range

**Objective:** Test hidden dimension validation

```python
def test_hidden_dim_validation():
    """Test that hidden_dim must be reasonable."""
    from orbit.model.fusion import GatedFusion
    
    # Valid
    model = GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=32)
    assert model is not None
    
    # Too small
    with pytest.raises(ValueError, match="hidden_dim must be >=8"):
        GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=4)
    
    # Too large (memory concern)
    with pytest.raises(ValueError, match="hidden_dim must be <=512"):
        GatedFusion(price_dim=15, news_dim=8, social_dim=12, hidden_dim=1024)
```

---

## Acceptance Criteria

- [ ] All unit tests pass (heads, fusion, gates)
- [ ] Integration test: Walk-forward training completes successfully
- [ ] Training: Loss decreases over epochs
- [ ] No gradient explosion (max gradient <100)
- [ ] No target leakage in features
- [ ] Training reproducible with fixed seed
- [ ] Performance: Training completes in <10 minutes
- [ ] Performance: Inference latency <10ms per symbol
- [ ] Hyperparameters validated correctly
- [ ] Models persist and load correctly
- [ ] Documentation: Test results logged to `tests/results/modeling.log`

---

## Related Files

* `08-modeling/heads_price_news_social.md` — Model head architecture
* `08-modeling/fusion_gated_blend.md` — Fusion mechanism
* `08-modeling/training_walkforward.md` — Training procedure
* `08-modeling/hyperparams_tuning.md` — Hyperparameter specifications
* `08-modeling/targets_labels.md` — Target definition
* `99-templates/TEMPLATE_test_plan.md` — Test plan template
