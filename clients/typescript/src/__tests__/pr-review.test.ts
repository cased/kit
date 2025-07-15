import { spawn } from 'child_process';
import { Kit } from '../kit';

jest.mock('child_process');
const mockSpawn = spawn as jest.MockedFunction<typeof spawn>;

// Helper to create mock child process
function createMockProcess(stdout: string, stderr: string = '', exitCode: number = 0) {
  const mockProcess = {
    stdout: {
      on: jest.fn((event, handler) => {
        if (event === 'data') {
          handler(Buffer.from(stdout));
        }
      }),
    },
    stderr: {
      on: jest.fn((event, handler) => {
        if (event === 'data' && stderr) {
          handler(Buffer.from(stderr));
        }
      }),
    },
    on: jest.fn((event, handler) => {
      if (event === 'close') {
        handler(exitCode);
      }
    }),
  };
  
  return mockProcess;
}

describe('Kit - PR Review', () => {
  let kit: Kit;

  beforeEach(() => {
    kit = new Kit();
    jest.clearAllMocks();
  });

  describe('reviewPR', () => {
    it('should review a PR with minimal options', async () => {
      const mockReview = `## 🛠️ Kit AI Code Review
      
## Priority Issues

### High Priority
- Security vulnerability in auth.py:45

## Summary
This PR needs security fixes.`;
      
      mockSpawn.mockReturnValue(createMockProcess(mockReview) as any);
      
      const review = await kit.reviewPR('https://github.com/owner/repo/pull/123');
      
      expect(mockSpawn).toHaveBeenCalledWith(
        'kit',
        ['pr-review', 'https://github.com/owner/repo/pull/123'],
        expect.objectContaining({
          env: expect.any(Object),
        })
      );
      expect(review).toContain('Security vulnerability');
    });

    it('should pass all PR review options', async () => {
      mockSpawn.mockReturnValue(createMockProcess('Review content') as any);
      
      await kit.reviewPR('https://github.com/owner/repo/pull/123', {
        githubToken: 'ghp_token',
        llmProvider: 'anthropic',
        model: 'claude-3-sonnet',
        apiKey: 'sk-ant-key',
        priorities: ['high', 'medium'],
        postAsComment: true,
        cloneForAnalysis: true,
        repoPath: '/local/repo',
      });
      
      expect(mockSpawn).toHaveBeenCalledWith(
        'kit',
        [
          'pr-review',
          'https://github.com/owner/repo/pull/123',
          '--llm-provider', 'anthropic',
          '--model', 'claude-3-sonnet',
          '--priority-filter', 'high,medium',
          '--post-as-comment',
          '--clone-for-analysis',
          '--repo-path', '/local/repo',
        ],
        expect.objectContaining({
          env: expect.objectContaining({
            GITHUB_TOKEN: 'ghp_token',
            ANTHROPIC_API_KEY: 'sk-ant-key',
          }),
        })
      );
    });

    it('should set correct environment variables for different providers', async () => {
      mockSpawn.mockReturnValue(createMockProcess('Review') as any);
      
      // Test OpenAI
      await kit.reviewPR('https://github.com/owner/repo/pull/1', {
        llmProvider: 'openai',
        apiKey: 'sk-openai',
      });
      
      expect(mockSpawn).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Array),
        expect.objectContaining({
          env: expect.objectContaining({
            OPENAI_API_KEY: 'sk-openai',
          }),
        })
      );
      
      // Test Google
      jest.clearAllMocks();
      await kit.reviewPR('https://github.com/owner/repo/pull/2', {
        llmProvider: 'google',
        apiKey: 'google-key',
      });
      
      expect(mockSpawn).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Array),
        expect.objectContaining({
          env: expect.objectContaining({
            GOOGLE_API_KEY: 'google-key',
          }),
        })
      );
    });

    it('should handle PR review errors', async () => {
      const mockProcess = createMockProcess('', 'GitHub API error: Not found', 1);
      mockSpawn.mockReturnValue(mockProcess as any);
      
      await expect(
        kit.reviewPR('https://github.com/owner/repo/pull/999')
      ).rejects.toThrow('GitHub API error');
    });
  });
}); 