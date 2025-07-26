# Docker Image Management Guide

This guide provides instructions for managing Docker images, including how to remove images to free up disk space or resolve issues with your deployment.

## Listing Docker Images

Before removing images, you may want to list all available images to identify which ones to remove:

```bash
# List all Docker images
docker images

# OR use the newer format
docker image ls
```

This will display a table with columns for:
- REPOSITORY: The image name
- TAG: The image version/tag
- IMAGE ID: A unique identifier for the image
- CREATED: When the image was created
- SIZE: The size of the image

## Removing Docker Images

### Remove a Specific Image by ID or Name

```bash
# Remove by image ID
docker rmi <image-id>

# Remove by repository and tag
docker rmi <repository>:<tag>

# Example:
docker rmi abc123def456
docker rmi kebunsu-api:latest
```

### Remove Multiple Images at Once

```bash
# Remove multiple images by ID
docker rmi <image-id1> <image-id2> <image-id3>

# Example:
docker rmi abc123def456 ghi789jkl012
```

### Remove All Unused Images

```bash
# Remove all dangling images (untagged images)
docker image prune

# Remove all unused images (not just dangling ones)
docker image prune -a

# Force removal without confirmation prompt
docker image prune -f
```

### Remove All Images

```bash
# Remove all images (use with caution!)
docker rmi $(docker images -q)
```

## Handling Images Used by Containers

If an image is being used by a container (running or stopped), you'll get an error when trying to remove it. Here's how to handle this:

### Check if Images are Being Used

```bash
# List all containers (running and stopped)
docker ps -a
```

### Stop and Remove Containers First

```bash
# Stop a running container
docker stop <container-id>

# Remove a container
docker rm <container-id>

# Stop and remove in one command
docker rm -f <container-id>

# Stop all running containers
docker stop $(docker ps -q)

# Remove all stopped containers
docker container prune
```

### Force Remove an Image (Even if Used by Containers)

```bash
# Force remove an image
docker rmi -f <image-id>
```

**Note**: This is not recommended as it can leave containers in an inconsistent state.

## Cleaning Up Your Docker Environment

If you're troubleshooting issues or want to start fresh, you might want to clean up your entire Docker environment:

```bash
# Stop all running containers
docker stop $(docker ps -q)

# Remove all containers
docker rm $(docker ps -a -q)

# Remove all images
docker rmi $(docker images -q)

# Remove all volumes
docker volume prune -f

# Remove all networks
docker network prune -f

# Complete system prune (containers, images, networks, and volumes)
docker system prune -a --volumes
```

**Warning**: The last command will remove all unused containers, networks, images, and volumes. Use with caution in production environments.

## Rebuilding Images for Your XerpeX ERP Deployment

If you're experiencing issues with your deployment and want to rebuild your images:

```bash
# Navigate to your project directory
cd /path/to/xerpex-be

# Stop existing containers
docker compose down

# Remove the images
docker rmi kebunsu-api:latest

# Rebuild without using cache
docker compose build --no-cache

# Start the containers again
docker compose up -d
```

## Troubleshooting Common Image Issues

### Image Build Failures

If your image build fails:

1. Check the build logs for errors
2. Ensure all required files are present
3. Verify your Dockerfile syntax
4. Check for network issues if pulling base images

### "No space left on device" Error

If you get a "no space left on device" error:

```bash
# Check Docker disk usage
docker system df

# Clean up unused Docker resources
docker system prune -a
```

### Cannot Remove Image (in use by container)

If you can't remove an image because it's in use:

1. List all containers using the image:
   ```bash
   docker ps -a --filter ancestor=<image-id>
   ```

2. Stop and remove those containers:
   ```bash
   docker rm -f $(docker ps -a --filter ancestor=<image-id> -q)
   ```

3. Then remove the image:
   ```bash
   docker rmi <image-id>
   ```

## Best Practices for Image Management

1. **Tag your images properly**: Use meaningful tags instead of relying on "latest"
2. **Use multi-stage builds**: Reduces final image size
3. **Clean up regularly**: Set up periodic cleanup of unused images
4. **Use .dockerignore**: Prevent unnecessary files from being included in builds
5. **Monitor disk space**: Keep an eye on Docker's disk usage with `docker system df`

## Specific to XerpeX ERP Deployment

If you're specifically trying to fix the 502 Bad Gateway error:

1. Check if the issue is with the image or configuration:
   ```bash
   # Check container logs
   docker logs kebunsu-api
   ```

2. If logs indicate image issues, rebuild:
   ```bash
   docker compose down
   docker rmi kebunsu-api:latest
   docker compose build --no-cache
   docker compose up -d
   ```

3. Verify the application is running inside the container:
   ```bash
   docker exec -it kebunsu-api bash
   # Inside the container
   curl http://localhost:8000/health
   ```

Remember that removing and rebuilding images is just one troubleshooting step. The 502 error could also be caused by network configuration, Nginx settings, or application issues.