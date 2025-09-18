import collections

if __name__ == "__main__":
    counter=collections.Counter('abcdeabcdabcaba')
    print(counter.most_common(3))
    print(sorted(counter))
    
