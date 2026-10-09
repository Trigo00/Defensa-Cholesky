#define _POSIX_C_SOURCE 200809L
#include <stdio.h>
#include <stdlib.h>
#include <time.h>
#include <sys/wait.h>
#include <unistd.h>
#include <errno.h>
static double now(void) {struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return t.tv_sec+t.tv_nsec*1e-9;}
int main(int argc,char **argv) {
    if(argc<3) return 2;
    double start=now();pid_t pid=fork();
    if(pid<0) return 3;
    if(!pid) {execvp(argv[2],argv+2);perror("execvp");_exit(127);}
    int status;while(waitpid(pid,&status,0)<0) if(errno!=EINTR) return 3;
    double elapsed=now()-start;
    int result=WIFEXITED(status)?WEXITSTATUS(status):128+WTERMSIG(status);
    FILE *out=fopen(argv[1],"w");if(!out) return 3;
    fprintf(out,"external_s,exit_code\n%.12g,%d\n",elapsed,result);fclose(out);
    return result;
}
