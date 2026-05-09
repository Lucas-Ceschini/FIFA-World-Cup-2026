import json
import argparse
import sys
from pathlib import Path
import numpy as np
from bs4 import BeautifulSoup
from datetime import datetime
from scipy.optimize import minimize
from collections import defaultdict, Counter