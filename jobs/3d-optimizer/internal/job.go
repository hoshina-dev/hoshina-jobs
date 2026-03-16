package internal

import (
	"context"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"time"
)

const (
	workDir       = "/tmp/3d-optimizer"
	sourceFile    = "source.glb"
	reducedFile   = "reduced.glb"
	optimizedFile = "optimized.glb"
)

type JobService struct {
	config *Config
	client *http.Client
}

func NewJobService(cfg *Config) *JobService {
	return &JobService{
		config: cfg,
		client: &http.Client{
			Timeout: 5 * time.Minute,
		},
	}
}


func (s *JobService) Run(ctx context.Context) error {
	log.Println("Starting job execution")

	if err := os.MkdirAll(workDir, 0755); err != nil {
		return fmt.Errorf("create work directory: %w", err)
	}
	defer os.RemoveAll(workDir)

	if err := s.downloadSourceFile(ctx); err != nil {
		return fmt.Errorf("download source file: %w", err)
	}

	if err := s.processOptimization(ctx); err != nil {
		return fmt.Errorf("process optimization: %w", err)
	}

	if err := s.uploadResultFile(ctx); err != nil {
		return fmt.Errorf("upload result file: %w", err)
	}

	log.Println("Job execution completed successfully")
	return nil
}

func (s *JobService) downloadSourceFile(ctx context.Context) error {
	log.Printf("Downloading source file from: %s", s.config.SourceGLMURL)
	
	req, err := http.NewRequestWithContext(ctx, "GET", s.config.SourceGLMURL, nil)
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("download file: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("unexpected status code: %d", resp.StatusCode)
	}

	destPath := filepath.Join(workDir, sourceFile)
	out, err := os.Create(destPath)
	if err != nil {
		return fmt.Errorf("create file: %w", err)
	}
	defer out.Close()

	written, err := io.Copy(out, resp.Body)
	if err != nil {
		return fmt.Errorf("save file: %w", err)
	}

	log.Printf("Source file downloaded successfully (%d bytes)", written)
	return nil
}

func (s *JobService) processOptimization(ctx context.Context) error {
	log.Println("Processing 3D optimization")

	sourcePath := filepath.Join(workDir, sourceFile)
	reducedPath := filepath.Join(workDir, reducedFile)
	optimizedPath := filepath.Join(workDir, optimizedFile)

	if err := s.meshReduction(ctx, sourcePath, reducedPath); err != nil {
		return fmt.Errorf("mesh reduction: %w", err)
	}

	if err := s.dracoCompression(ctx, reducedPath, optimizedPath); err != nil {
		return fmt.Errorf("draco compression: %w", err)
	}

	log.Println("Optimization completed")
	return nil
}

func (s *JobService) meshReduction(ctx context.Context, inputPath, outputPath string) error {
	log.Printf("Starting mesh reduction (compression level: %d)...", s.config.Optimization.DracoCompressionLevel)

	cmd := exec.CommandContext(ctx, "gltf-pipeline",
		"-i", inputPath,
		"-o", outputPath,
		"--draco.compressionLevel", fmt.Sprintf("%d", s.config.Optimization.DracoCompressionLevel),
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		log.Printf("gltf-pipeline output: %s", string(output))
		return fmt.Errorf("gltf-pipeline failed: %w", err)
	}

	stat, err := os.Stat(outputPath)
	if err != nil {
		return fmt.Errorf("check reduced file: %w", err)
	}

	log.Printf("Mesh reduction completed (output: %d bytes)", stat.Size())
	return nil
}

func (s *JobService) dracoCompression(ctx context.Context, inputPath, outputPath string) error {
	opt := s.config.Optimization
	log.Printf("Starting DRACO compression (CL:%d, QP:%d, QT:%d, QN:%d, QG:%d)...",
		opt.DracoCompressionLevel, opt.DracoPositionQuant, opt.DracoTexCoordQuant,
		opt.DracoNormalQuant, opt.DracoGenericQuant)

	cmd := exec.CommandContext(ctx, "draco_encoder",
		"-i", inputPath,
		"-o", outputPath,
		"-cl", fmt.Sprintf("%d", opt.DracoCompressionLevel),
		"-qp", fmt.Sprintf("%d", opt.DracoPositionQuant),
		"-qt", fmt.Sprintf("%d", opt.DracoTexCoordQuant),
		"-qn", fmt.Sprintf("%d", opt.DracoNormalQuant),
		"-qg", fmt.Sprintf("%d", opt.DracoGenericQuant),
	)

	output, err := cmd.CombinedOutput()
	if err != nil {
		log.Printf("draco_encoder output: %s", string(output))
		return fmt.Errorf("draco_encoder failed: %w", err)
	}

	stat, err := os.Stat(outputPath)
	if err != nil {
		return fmt.Errorf("check optimized file: %w", err)
	}

	log.Printf("DRACO compression completed (output: %d bytes)", stat.Size())
	return nil
}

func (s *JobService) uploadResultFile(ctx context.Context) error {
	log.Printf("Uploading result file to: %s", s.config.DestGLMURL)
	
	optimizedPath := filepath.Join(workDir, optimizedFile)
	
	file, err := os.Open(optimizedPath)
	if err != nil {
		return fmt.Errorf("open optimized file: %w", err)
	}
	defer file.Close()

	stat, err := file.Stat()
	if err != nil {
		return fmt.Errorf("stat optimized file: %w", err)
	}

	req, err := http.NewRequestWithContext(ctx, "PUT", s.config.DestGLMURL, file)
	if err != nil {
		return fmt.Errorf("create request: %w", err)
	}
	req.Header.Set("Content-Type", "application/octet-stream")
	req.ContentLength = stat.Size()

	resp, err := s.client.Do(req)
	if err != nil {
		return fmt.Errorf("upload file: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK && resp.StatusCode != http.StatusCreated {
		body, _ := io.ReadAll(resp.Body)
		return fmt.Errorf("unexpected status code: %d, body: %s", resp.StatusCode, string(body))
	}

	log.Printf("Result file uploaded successfully (%d bytes)", stat.Size())
	return nil
}

