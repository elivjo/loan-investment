# loan-investment

Functional Requirements
- Allow the user to upload the data of his investments in the application.                                  
     - When doing this, the user will provide 2 CSV files:
          - One containing the loans.
          - One containing the cash flows of the loans.
     - Calculate the loan fields as necessary. 
- Allow the user to create a repayment for a loan, not through the CSV file.
    - The necessary loan calculations should take place in this case as well. 
- Allow the user to view his loans and filter them by any attribute.
- Allow the user to view the cash flows and filter them by any attribute.
- Allow the user to view statistics on his investments:
    - Number of Loans
    - Total invested amount (all loans)
    - Current invested amount (only open loans)
    - Total repaid amount (all loans)
    - Average Realized IRR
        - Weighted average of realized IRR, using the loan invested amount as weight.
        - Consider only closed loans. 

Non-functional Requirements
- The application should expose a REST API for the required functionalities.
    - The application should support authentication and authorization.
        - 2 types of users:
            - Investor - Can do anything on the application.
            - Analyst - Read-only permissions. 
- The processing of the CSV files should happen asynchronously.
- The statistics should be stored in a cache. 
   - Whenever new loans/cash flows arrive, the cache should be invalidated.
- The project should be set up with the usage of docker and docker-compose.
    