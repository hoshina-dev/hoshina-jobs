package internal

import (
	"fmt"
	"os"
	"strconv"
)

type Config struct {
	SourceGLMURL string
	DestGLMURL   string
	UUID         string
	WebhookURL   string
	Optimization OptimizationConfig
}

type OptimizationConfig struct {
	DracoCompressionLevel int
	DracoPositionQuant    int
	DracoTexCoordQuant    int
	DracoNormalQuant      int
	DracoGenericQuant     int
}

func Load() (*Config, error) {
	sourceGLMURL := os.Getenv("SOURCE_GLM_URL")
	if sourceGLMURL == "" {
		return nil, fmt.Errorf("SOURCE_GLM_URL environment variable is required")
	}

	destGLMURL := os.Getenv("DEST_GLM_URL")
	if destGLMURL == "" {
		return nil, fmt.Errorf("DEST_GLM_URL environment variable is required")
	}

	uuid := os.Getenv("UUID")
	if uuid == "" {
		return nil, fmt.Errorf("UUID environment variable is required")
	}

	webhookURL := os.Getenv("WEBHOOK_URL")
	if webhookURL == "" {
		return nil, fmt.Errorf("WEBHOOK_URL environment variable is required")
	}

	optimization := OptimizationConfig{
		DracoCompressionLevel: getEnvInt("DRACO_COMPRESSION_LEVEL", 10),
		DracoPositionQuant:    getEnvInt("DRACO_POSITION_QUANTIZATION", 14),
		DracoTexCoordQuant:    getEnvInt("DRACO_TEXCOORD_QUANTIZATION", 12),
		DracoNormalQuant:      getEnvInt("DRACO_NORMAL_QUANTIZATION", 10),
		DracoGenericQuant:     getEnvInt("DRACO_GENERIC_QUANTIZATION", 8),
	}

	return &Config{
		SourceGLMURL: sourceGLMURL,
		DestGLMURL:   destGLMURL,
		UUID:         uuid,
		WebhookURL:   webhookURL,
		Optimization: optimization,
	}, nil
}

func getEnvInt(key string, defaultValue int) int {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	
	intValue, err := strconv.Atoi(value)
	if err != nil {
		return defaultValue
	}
	
	return intValue
}
