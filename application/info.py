claude_4_7_opus_models = [   # Opus 4.7
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "claude",
        "model_id": "us.anthropic.claude-opus-4-7"
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "claude",
        "model_id": "us.anthropic.claude-opus-4-7"
    }
]

claude_4_6_sonnet_models = [   # Sonnet 4.6
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "claude",
        "model_id": "us.anthropic.claude-sonnet-4-6"
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "claude",
        "model_id": "us.anthropic.claude-sonnet-4-6"
    }
]

claude_4_6_opus_models = [   # Opus 4.6
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "claude",
        "model_id": "us.anthropic.claude-opus-4-6-v1"
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "claude",
        "model_id": "us.anthropic.claude-opus-4-6-v1"
    }
]

claude_4_5_haiku_models = [   # Haiku 4.5
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "claude",
        "model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "claude",
        "model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "claude",
        "model_id": "us.anthropic.claude-haiku-4-5-20251001-v1:0"
    }
]

claude_4_5_opus_models = [   # Opus 4.5
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "claude",
        "model_id": "us.anthropic.claude-opus-4-5-20251101-v1:0"
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "claude",
        "model_id": "us.anthropic.claude-opus-4-5-20251101-v1:0"
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "claude",
        "model_id": "us.anthropic.claude-opus-4-5-20251101-v1:0"
    }
]

claude_4_5_sonnet_models = [   # Sonnet 4.5
    {
        "bedrock_region": "us-west-2", # Oregon
        "model_type": "claude",
        "model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    },
    {
        "bedrock_region": "us-east-1", # N.Virginia
        "model_type": "claude",
        "model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    },
    {
        "bedrock_region": "us-east-2", # Ohio
        "model_type": "claude",
        "model_id": "us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    }
]

def get_model_info(model_name):
    models = []

    if model_name == "Claude 4.5 Opus":
        models = claude_4_5_opus_models
    elif model_name == "Claude 4.5 Sonnet":
        models = claude_4_5_sonnet_models
    elif model_name == "Claude 4.5 Haiku":
        models = claude_4_5_haiku_models
    elif model_name == "Claude 4.6 Sonnet":
        models = claude_4_6_sonnet_models
    elif model_name == "Claude 4.6 Opus":
        models = claude_4_6_opus_models
    elif model_name == "Claude 4.7 Opus":
        models = claude_4_7_opus_models

    return models

STOP_SEQUENCE_CLAUDE = "\n\nHuman:" 
STOP_SEQUENCE_NOVA = '"\n\n<thinking>", "\n<thinking>", " <thinking>"'

def get_stop_sequence(model_name):
    models = get_model_info(model_name)

    model_type = models[0]["model_type"]

    if model_type == "claude":
        return STOP_SEQUENCE_CLAUDE
    else:
        return ""
