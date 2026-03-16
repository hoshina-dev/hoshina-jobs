package main

import (
	"context"
	"log"
	"os"

	"hoshina-jobs/3d-optimizer/internal"
)

func main() {
	log.Println("Starting 3D Optimizer Job")

	cfg, err := internal.Load()
	if err != nil {
		log.Fatalf("Failed to load configuration: %v", err)
		os.Exit(1)
	}

	log.Printf("Job UUID: %s", cfg.UUID)
	log.Printf("Source GLM URL: %s", cfg.SourceGLMURL)
	log.Printf("Destination GLM URL: %s", cfg.DestGLMURL)
	log.Printf("Webhook URL: %s", cfg.WebhookURL)

	ctx := context.Background()
	jobService := internal.NewJobService(cfg)

	if err := jobService.Run(ctx); err != nil {
		log.Printf("Job failed: %v", err)
		os.Exit(1)
	}

	log.Println("Job completed successfully")
	os.Exit(0)
}
